"""EXP-IGNITE-002: polarity-assisted pair liveness instrument."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import e1_reservoir as H
import exp_glu_001 as G
import exp_ignite_001 as I
from flylab.dynamics import LIFParams
from flylab.graph import load_graph
from flylab.spectral import spectral_radius, syn_scale_for_gain
from memory_task import simulate_terminal_features

EXPERIMENT_ID = "EXP-IGNITE-002"
PROTOCOL = ROOT / "experiments/results/EXP-IGNITE-002/protocol.md"
RESULTS = ROOT / "experiments/results/EXP-IGNITE-002"
ALL_GAINS = tuple(float(x) for x in np.geomspace(0.05, 80.0, 16))  # SOURCE: frozen protocol.md
SMOKE_SEEDS = (0,)  # SOURCE: frozen protocol.md
SIZING_SEEDS = (0, 1, 2)  # SOURCE: frozen protocol.md
CONFIRM_SEEDS = tuple(range(12))  # SOURCE: frozen protocol.md
SMOKE_TRIALS = 2  # SOURCE: frozen protocol.md
FULL_TRIALS = 10  # SOURCE: frozen protocol.md
N_NODES = 500  # SOURCE: existing selected induced subgraph
N_INPUTS = 50  # SOURCE: frozen protocol.md
N_PROBES = 48  # SOURCE: frozen protocol.md
LAG = 100  # SOURCE: fixed operating-point stimulus; no memory metric
TARGET_RATE = 0.002  # SOURCE: frozen protocol.md
RATE_BAND = 0.20  # SOURCE: frozen protocol.md
POLICIES = ("glutamate_unknown", "glutamate_inhibitory")


def sha256_file(path: Path) -> str:
    return I.sha256_file(path)


def write_json_once(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if path.exists() or tmp.exists():
        raise FileExistsError(f"refusing to overwrite checkpoint: {path}")
    with tmp.open("x", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_checkpoint(path: Path, protocol_hash: str, runner_hash: str):
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("protocol_sha256") != protocol_hash or data.get("runner_sha256") != runner_hash:
        raise RuntimeError(f"checkpoint provenance mismatch; refusing resume: {path}")
    return data


def evaluate_seed(seed: int, stage: str, gains: tuple[float, ...], cfg: dict,
                  graphs: dict, meta: dict, inputs, cue0, cue1, probes,
                  protocol_hash: str, runner_hash: str, trials: int):
    base = dict(cfg["dynamics"]["lif"])
    lif0 = LIFParams(**base)
    cue_amp = (lif0.v_th - lif0.v_rest) * lif0.tau_m / (lif0.r * lif0.dt)
    train_drive, _ = I.M.make_trials(N_NODES, cue0, cue1, trials, LAG, cue_amp,
                                     protocol_hash, seed, f"{stage}-train")
    test_drive, _ = I.M.make_trials(N_NODES, cue0, cue1, trials, LAG, cue_amp,
                                    protocol_hash, seed, f"{stage}-test")
    rows = {policy: {} for policy in POLICIES}
    for policy in POLICIES:
        W = graphs[policy]
        rho = spectral_radius(W, signed=False)
        for gain in gains:
            syn_scale = syn_scale_for_gain(rho, gain, lif0.tau_m, lif0.dt, lif0.r)
            lif = LIFParams(**{**base, "syn_scale": syn_scale})
            t0 = time.perf_counter()
            Xtr, sttr = simulate_terminal_features(
                W, train_drive, lif, inputs, probes,
                I.derive_seed(protocol_hash, "ignite002", stage, seed, policy, gain, "train"),
            )
            Xte, stte = simulate_terminal_features(
                W, test_drive, lif, inputs, probes,
                I.derive_seed(protocol_hash, "ignite002", stage, seed, policy, gain, "test"),
            )
            tr_live = I.live_report(Xtr, sttr, f"{policy}_train_seed{seed}_gain{gain}")
            te_live = I.live_report(Xte, stte, f"{policy}_test_seed{seed}_gain{gain}")
            train_rate = I.rate(sttr, len(train_drive), LAG)
            test_rate = I.rate(stte, len(test_drive), LAG)
            train_error = abs(train_rate - TARGET_RATE) / TARGET_RATE
            test_error = abs(test_rate - TARGET_RATE) / TARGET_RATE
            rate_match = bool(train_error <= RATE_BAND and test_error <= RATE_BAND)
            alive = bool(tr_live["alive"] and te_live["alive"])
            candidate = bool(alive and rate_match)
            rows[policy][str(gain)] = {
                "policy": policy, "gain": gain,
                "status": "LIVE" if candidate else "MISSING",
                "pair_candidate": candidate, "alive": alive, "rate_match": rate_match,
                "train_rate": train_rate, "test_rate": test_rate,
                "train_relative_rate_error": float(train_error),
                "test_relative_rate_error": float(test_error),
                "train_liveness": tr_live, "test_liveness": te_live,
                "syn_scale": float(syn_scale), "rho_abs": float(rho),
                "active_edges": int(W.nnz), "wall_seconds": time.perf_counter() - t0,
                "accuracy_computed": False,
                "reason": None if candidate else "liveness or rate-band gate failed",
            }
    pairs = []
    for gu, unknown in rows[POLICIES[0]].items():
        for gi, inhibitory in rows[POLICIES[1]].items():
            if unknown["pair_candidate"] and inhibitory["pair_candidate"]:
                pairs.append({"seed": int(seed), "gain_unknown": float(gu),
                              "gain_inhibitory": float(gi), "pair_alive": True,
                              "unknown_train_rate": unknown["train_rate"],
                              "unknown_test_rate": unknown["test_rate"],
                              "inhibitory_train_rate": inhibitory["train_rate"],
                              "inhibitory_test_rate": inhibitory["test_rate"]})
    return {
        "experiment_id": EXPERIMENT_ID, "stage": stage, "seed": int(seed),
        "trials_per_class_per_split": int(trials), "lag_steps": LAG,
        "results": rows, "pair_cells": pairs, "no_accuracy_or_auc_computed": True,
        "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
    }


def aggregate(stage_dir: Path, seeds, protocol_hash: str, runner_hash: str):
    rows = []
    for seed in seeds:
        p = stage_dir / f"seed_{seed:04d}.json"
        if p.exists():
            rows.append(read_checkpoint(p, protocol_hash, runner_hash))
    pairs = [p for row in rows for p in row.get("pair_cells", [])]
    return {
        "experiment_id": EXPERIMENT_ID, "stage": stage_dir.name,
        "status": "PAIR_FOUND" if pairs else "NO_COIGNITE",
        "scientific_result": False, "seeds_written": len(rows),
        "expected_seeds": len(seeds), "pair_cells": pairs,
        "pair_cell_count": len(pairs), "no_accuracy_or_auc_computed": True,
        "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
    }


def make_root():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rev = H.provenance().get("git_rev", "unknown")
    root = RESULTS / f"ignite002_{stamp}_{rev}"
    root.mkdir(parents=True)
    return root


def check_root(path: Path):
    resolved = path.resolve()
    if RESULTS.resolve() not in resolved.parents or not resolved.name.startswith("ignite002_"):
        raise ValueError(f"run root must be ignite002_* below {RESULTS.resolve()}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def run(stage: str, run_root: Path, candidate_summary: Path | None):
    cfg = H.load_cfg()
    protocol_hash = sha256_file(PROTOCOL)
    runner_hash = sha256_file(Path(__file__))
    root = check_root(run_root)
    if stage == "smoke":
        seeds, trials, gains = SMOKE_SEEDS, SMOKE_TRIALS, ALL_GAINS
    elif stage == "sizing":
        seeds, trials, gains = SIZING_SEEDS, FULL_TRIALS, ALL_GAINS
    elif stage == "confirm":
        seeds, trials, gains = CONFIRM_SEEDS, FULL_TRIALS, ALL_GAINS
        if candidate_summary is not None:
            candidate_pairs = json.loads(candidate_summary.read_text(encoding="utf-8")).get("pair_cells", [])
            selected = sorted({float(p["gain_unknown"]) for p in candidate_pairs} |
                              {float(p["gain_inhibitory"]) for p in candidate_pairs})
            if selected:
                gains = tuple(selected)
    else:
        raise ValueError(stage)
    stage_dir = root / stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    g = G.load_graph(load_neurons=True)
    nodes = H.select_nodes(g, N_NODES)
    graphs, meta, nt_counts = G.build_policy_graphs(g, nodes)
    inputs, cue0, cue1, probes, map_meta = I.make_input_map(protocol_hash)
    graph_sha = {name: sha256_file(ROOT / "data/derived/graph" / name)
                 for name in ("csr_unsigned.npz", "csc_unsigned.npz", "coo_signed.npz")}
    start = stage_dir / "stage_started.json"
    if not start.exists():
        write_json_once(start, {
            "experiment_id": EXPERIMENT_ID, "stage": stage,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
            "config_sha256": sha256_file(H.CFG_PATH), "graph_sha256": graph_sha,
            "map": map_meta, "policies": list(POLICIES), "seeds": list(seeds),
            "gains": list(gains), "target_rate": TARGET_RATE, "rate_band": RATE_BAND,
            "nt_counts": nt_counts, "policy_meta": {p: meta[p] for p in POLICIES},
        })
    for seed in seeds:
        path = stage_dir / f"seed_{seed:04d}.json"
        if read_checkpoint(path, protocol_hash, runner_hash) is not None:
            continue
        row = evaluate_seed(seed, stage, gains, cfg, graphs, meta, inputs, cue0, cue1,
                            probes, protocol_hash, runner_hash, trials)
        write_json_once(path, row)
        print(json.dumps({"stage": stage, "seed": seed,
                          "pair_cells": len(row["pair_cells"]),
                          "tested_gains": len(gains)}), flush=True)
    summary = aggregate(stage_dir, seeds, protocol_hash, runner_hash)
    if not (stage_dir / "summary.json").exists():
        write_json_once(stage_dir / "summary.json", summary)
    print(json.dumps({"run_root": str(root), "stage": stage, **summary}, indent=2), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=("smoke", "sizing", "confirm"), required=True)
    ap.add_argument("--run-root", type=Path)
    ap.add_argument("--candidate-summary", type=Path)
    args = ap.parse_args(argv)
    if not PROTOCOL.is_file():
        ap.error(f"missing frozen preregistration: {PROTOCOL}")
    run(args.stage, args.run_root or make_root(), args.candidate_summary)


if __name__ == "__main__":
    main()
