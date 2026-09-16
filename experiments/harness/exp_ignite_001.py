"""EXP-IGNITE-001: find co-ignited connectome/DP operating cells."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
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
import exp_mem_001_confirm as M
from flylab.dynamics import LIFParams
from flylab.graph import induced_subgraph, load_graph
from flylab.spectral import spectral_radius, syn_scale_for_gain
from memory_task import simulate_terminal_features

EXPERIMENT_ID = "EXP-IGNITE-001"
PROTOCOL = ROOT / "experiments/results/EXP-IGNITE-001/protocol.md"
RESULTS = ROOT / "experiments/results/EXP-IGNITE-001"
ALL_GAINS = tuple(float(x) for x in np.geomspace(0.05, 80.0, 16))  # SOURCE: frozen protocol.md
SMOKE_SEEDS = (0,)  # SOURCE: frozen protocol.md
SIZING_SEEDS = (0, 1, 2)  # SOURCE: frozen protocol.md
CONFIRM_SEEDS = tuple(range(12))  # SOURCE: frozen protocol.md
SMOKE_TRIALS = 2  # SOURCE: frozen protocol.md
FULL_TRIALS = 10  # SOURCE: frozen protocol.md
N_NODES = 500  # SOURCE: existing selected induced subgraph
N_INPUTS = 50  # SOURCE: frozen protocol.md
N_PROBES = 48  # SOURCE: frozen protocol.md
CALIBRATION_LAG = 100  # SOURCE: existing memory instrument operating point
TARGET_RATE = 0.002  # SOURCE: frozen protocol.md
RATE_BAND = 0.20  # GUESS: frozen ignition band; needs calibration data
ARM_NAMES = ("connectome_signed", "degree_preserving")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def derive_seed(protocol_hash: str, *labels) -> int:
    payload = protocol_hash + "|" + "|".join(map(str, labels))
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "little")


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


def live_report(X, stats, tag):
    guards = dict(H.load_cfg().get("harness_guards", {}))
    guards.update({"on_dead": "record", "min_unique_feature_rows": 2})
    with contextlib.redirect_stdout(io.StringIO()):
        return H.check_alive(X, stats, tag, guards)


def rate(stats, n_trials: int, lag: int) -> float:
    denom = int(n_trials) * (int(lag) + 1) * int(stats["pool_size"])
    return float(stats["pool_spikes"] / denom) if denom else 0.0


def make_input_map(protocol_hash: str):
    graph = load_graph(load_neurons=False)
    nodes = H.select_nodes(graph, N_NODES)
    A, _ = induced_subgraph(graph, nodes)
    ranked = sorted(
        range(N_NODES),
        key=lambda j: hashlib.sha256(f"{protocol_hash}|ignite-hash|{j}".encode()).digest(),
    )
    selected = ranked[:N_INPUTS]
    inputs = np.sort(np.asarray(selected, dtype=np.int64))
    cue0 = np.asarray(selected[:25], dtype=np.int64)
    cue1 = np.asarray(selected[25:], dtype=np.int64)
    probe_seed = derive_seed(protocol_hash, "probe-map") % (2**32)
    probes, _ = H.probe_set(N_NODES, inputs, N_PROBES, int(probe_seed))
    if np.intersect1d(inputs, probes).size:
        raise RuntimeError("input/probe leak")
    return inputs, cue0, cue1, probes, {
        "rule": "protocol-hash-ranked local nodes, first 50; 25/25 cue split",
        "forbidden_metric_maps": ["top_positive_outdegree", "top_positive_weight_sum"],
        "selected_local_nodes": inputs.tolist(),
    }


def variant_pair(variants):
    wanted = {"connectome-0": "connectome_signed", "dp-0": "degree_preserving"}
    out = {}
    for v in variants:
        if v["name"] in wanted:
            out[wanted[v["name"]]] = v
    if set(out) != set(ARM_NAMES):
        raise RuntimeError(f"primary variants missing: {set(ARM_NAMES) - set(out)}")
    return out


def evaluate_seed(seed: int, stage: str, gains: tuple[float, ...], cfg: dict,
                  variants: dict, inputs, cue0, cue1, probes,
                  protocol_hash: str, runner_hash: str, trials: int):
    base = dict(cfg["dynamics"]["lif"])
    lif0 = LIFParams(**base)
    cue_amp = (lif0.v_th - lif0.v_rest) * lif0.tau_m / (lif0.r * lif0.dt)
    train_drive, _ = M.make_trials(N_NODES, cue0, cue1, trials, CALIBRATION_LAG,
                                   cue_amp, protocol_hash, seed, f"{stage}-train")
    test_drive, _ = M.make_trials(N_NODES, cue0, cue1, trials, CALIBRATION_LAG,
                                  cue_amp, protocol_hash, seed, f"{stage}-test")
    out = {arm: {} for arm in ARM_NAMES}
    for arm in ARM_NAMES:
        variant = variants[arm]
        rho = spectral_radius(variant["W"], signed=False)
        for gain in gains:
            syn_scale = syn_scale_for_gain(
                rho, gain, lif0.tau_m, lif0.dt, lif0.r
            )
            lif = LIFParams(**{**base, "syn_scale": syn_scale})
            t0 = time.perf_counter()
            Xtr, sttr = simulate_terminal_features(
                variant["W"], train_drive, lif, inputs, probes,
                derive_seed(protocol_hash, "ignite", stage, seed, arm, gain, "train"),
            )
            Xte, stte = simulate_terminal_features(
                variant["W"], test_drive, lif, inputs, probes,
                derive_seed(protocol_hash, "ignite", stage, seed, arm, gain, "test"),
            )
            tr_live = live_report(Xtr, sttr, f"{arm}_train_seed{seed}_gain{gain}")
            te_live = live_report(Xte, stte, f"{arm}_test_seed{seed}_gain{gain}")
            train_rate = rate(sttr, len(train_drive), CALIBRATION_LAG)
            test_rate = rate(stte, len(test_drive), CALIBRATION_LAG)
            train_error = abs(train_rate - TARGET_RATE) / TARGET_RATE
            test_error = abs(test_rate - TARGET_RATE) / TARGET_RATE
            rate_match = bool(train_error <= RATE_BAND and test_error <= RATE_BAND)
            alive = bool(tr_live["alive"] and te_live["alive"])
            pair_candidate = bool(alive and rate_match)
            out[arm][str(gain)] = {
                "arm": arm, "gain": gain, "status": "LIVE" if pair_candidate else "MISSING",
                "pair_candidate": pair_candidate, "alive": alive, "rate_match": rate_match,
                "train_rate": train_rate, "test_rate": test_rate,
                "train_relative_rate_error": float(train_error),
                "test_relative_rate_error": float(test_error),
                "train_liveness": tr_live, "test_liveness": te_live,
                "syn_scale": float(syn_scale), "rho_abs": float(rho),
                "active_edges": int(variant["W"].nnz),
                "wall_seconds": time.perf_counter() - t0,
                "accuracy_computed": False,
                "reason": None if pair_candidate else "liveness or rate-band gate failed",
            }
    pairs = []
    cands_c = out["connectome_signed"]
    cands_d = out["degree_preserving"]
    for cg, c in cands_c.items():
        for dg, d in cands_d.items():
            if c["pair_candidate"] and d["pair_candidate"]:
                pairs.append({"seed": int(seed), "connectome_gain": float(cg),
                              "dp_gain": float(dg), "pair_alive": True,
                              "connectome_train_rate": c["train_rate"],
                              "connectome_test_rate": c["test_rate"],
                              "dp_train_rate": d["train_rate"],
                              "dp_test_rate": d["test_rate"]})
    return {
        "experiment_id": EXPERIMENT_ID, "stage": stage, "seed": int(seed),
        "trials_per_class_per_split": int(trials), "lag_steps": CALIBRATION_LAG,
        "results": out, "pair_cells": pairs,
        "no_accuracy_or_auc_computed": True,
        "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
    }


def aggregate(stage_dir: Path, seeds, protocol_hash: str, runner_hash: str):
    rows = []
    for seed in seeds:
        p = stage_dir / f"seed_{seed:04d}.json"
        if p.exists():
            rows.append(read_checkpoint(p, protocol_hash, runner_hash))
    pairs = [pair for row in rows for pair in row.get("pair_cells", [])]
    status = "PAIR_FOUND" if pairs else "NO_COIGNITE"
    return {
        "experiment_id": EXPERIMENT_ID, "stage": stage_dir.name,
        "status": status, "scientific_result": False,
        "seeds_written": len(rows), "expected_seeds": len(seeds),
        "pair_cells": pairs, "pair_cell_count": len(pairs),
        "no_accuracy_or_auc_computed": True,
        "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
    }


def make_root():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rev = H.provenance().get("git_rev", "unknown")
    root = RESULTS / f"ignite_{stamp}_{rev}"
    root.mkdir(parents=True)
    return root


def check_root(path: Path):
    resolved = path.resolve()
    if RESULTS.resolve() not in resolved.parents or not resolved.name.startswith("ignite_"):
        raise ValueError(f"run root must be an ignite_* directory below {RESULTS.resolve()}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def read_candidate_pairs(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("pair_cells", [])


def run(stage: str, run_root: Path, candidate_summary: Path | None):
    cfg = H.load_cfg()
    protocol_hash = sha256_file(PROTOCOL)
    runner_hash = sha256_file(Path(__file__))
    root = check_root(run_root)
    if stage == "smoke":
        seeds, trials = SMOKE_SEEDS, SMOKE_TRIALS
        gains = ALL_GAINS
    elif stage == "sizing":
        seeds, trials = SIZING_SEEDS, FULL_TRIALS
        gains = ALL_GAINS
    elif stage == "confirm":
        seeds, trials = CONFIRM_SEEDS, FULL_TRIALS
        gains = ALL_GAINS
        if candidate_summary is not None:
            candidate_pairs = read_candidate_pairs(candidate_summary)
            selected = sorted({float(p["connectome_gain"]) for p in candidate_pairs} |
                              {float(p["dp_gain"]) for p in candidate_pairs})
            if selected:
                gains = tuple(selected)
    else:
        raise ValueError(stage)
    stage_dir = root / stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    graph = load_graph(load_neurons=False)
    nodes = H.select_nodes(graph, N_NODES)
    inputs, cue0, cue1, probes, map_meta = make_input_map(protocol_hash)
    graph_sha = {name: sha256_file(ROOT / "data/derived/graph" / name)
                 for name in ("csr_unsigned.npz", "csc_unsigned.npz", "coo_signed.npz")}
    start = stage_dir / "stage_started.json"
    if not start.exists():
        write_json_once(start, {
            "experiment_id": EXPERIMENT_ID, "stage": stage,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
            "config_sha256": sha256_file(H.CFG_PATH), "graph_sha256": graph_sha,
            "map": map_meta, "seeds": list(seeds), "gains": list(gains),
            "all_registered_gains": list(ALL_GAINS), "target_rate": TARGET_RATE,
            "rate_band": RATE_BAND, "primary_arms": list(ARM_NAMES),
            "secondary_arms": {"weight_perm": "optional_not_run", "er": "optional_not_run", "ring": "optional_not_run"},
        })
    for seed in seeds:
        variants, graph_diag = M.create_graph_variants(graph, nodes, protocol_hash, seed, replicates=1)
        primary = variant_pair(variants)
        path = stage_dir / f"seed_{seed:04d}.json"
        if read_checkpoint(path, protocol_hash, runner_hash) is not None:
            continue
        row = evaluate_seed(seed, stage, gains, cfg, primary, inputs, cue0, cue1,
                            probes, protocol_hash, runner_hash, trials)
        row["graph_diagnostics"] = graph_diag
        row["graph_sha256"] = graph_sha
        row["map"] = map_meta
        write_json_once(path, row)
        print(json.dumps({"stage": stage, "seed": seed,
                          "pair_cells": len(row["pair_cells"]),
                          "tested_gains": len(gains)}), flush=True)
    summary = aggregate(stage_dir, seeds, protocol_hash, runner_hash)
    summary_path = stage_dir / "summary.json"
    if not summary_path.exists():
        write_json_once(summary_path, summary)
    print(json.dumps({"run_root": str(root), "stage": stage, **summary}, indent=2), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=("smoke", "sizing", "confirm"), required=True)
    ap.add_argument("--run-root", type=Path)
    ap.add_argument("--candidate-summary", type=Path)
    args = ap.parse_args(argv)
    if not PROTOCOL.is_file():
        ap.error(f"missing frozen preregistration: {PROTOCOL}")
    if args.stage == "confirm" and args.candidate_summary is not None and not args.candidate_summary.is_file():
        ap.error(f"missing candidate summary: {args.candidate_summary}")
    run(args.stage, args.run_root or make_root(), args.candidate_summary)


if __name__ == "__main__":
    main()
