"""EXP-MEM-003: preregistered connectome-vs-DP memory curve."""
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
from scipy.stats import t

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

EXPERIMENT_ID = "EXP-MEM-003"
PROTOCOL = ROOT / "experiments/results/EXP-MEM-003/protocol.md"
RESULTS = ROOT / "experiments/results/EXP-MEM-003"
DELAYS = (10, 25, 50, 100, 250, 500)  # SOURCE: frozen protocol.md
SMOKE_DELAYS = (10, 100)  # SOURCE: frozen protocol.md smoke plan
SEEDS = tuple(range(12))  # SOURCE: frozen protocol.md
SMOKE_SEEDS = (0,)  # SOURCE: frozen protocol.md smoke plan
N_NODES = 500  # SOURCE: existing selected induced subgraph
N_INPUTS = 50  # SOURCE: frozen protocol.md
INPUT_GROUP_SIZE = 25  # SOURCE: frozen protocol.md
N_PROBES = 48  # SOURCE: existing registered instrument
CALIBRATION_LAG = 100  # SOURCE: frozen protocol.md
TRIALS_PER_CLASS = 10  # SOURCE: frozen protocol.md
SMOKE_TRIALS_PER_CLASS = 2  # SOURCE: frozen protocol.md smoke plan
CALIBRATION_TRIALS_PER_CLASS = 10  # SOURCE: frozen protocol.md
SMOKE_CALIBRATION_TRIALS_PER_CLASS = 2  # SOURCE: frozen protocol.md smoke plan
GAIN_GRID_MIN = 0.125  # GUESS: preregistered calibration lower bound; needs live calibration
GAIN_GRID_MAX = 64.0  # GUESS: preregistered gain cap; needs live calibration
GAIN_GRID_SIZE = 64  # GUESS: preregistered calibration resolution
RATE_MATCH_TOL = 0.10  # GUESS: preregistered instrument tolerance; needs calibration data
LIVENESS_MIN_UNIQUE = 2  # SOURCE: existing harness liveness guard
ARM_TYPES = ("connectome", "dp", "weight_perm", "er", "ring")


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
        raise FileExistsError(f"refusing to overwrite artifact/checkpoint: {path}")
    with tmp.open("x", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    if path.exists():
        raise FileExistsError(f"target appeared during write: {path}")
    os.replace(tmp, path)


def read_checkpoint(path: Path, protocol_hash: str, runner_hash: str):
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data.get("protocol_sha256") != protocol_hash
            or data.get("runner_sha256") != runner_hash):
        raise RuntimeError(f"checkpoint provenance mismatch; refusing resume: {path}")
    return data


def live_report(X, stats, tag):
    guards = dict(H.load_cfg().get("harness_guards", {}))
    guards.update({"on_dead": "record", "min_unique_feature_rows": LIVENESS_MIN_UNIQUE})
    with contextlib.redirect_stdout(io.StringIO()):
        return H.check_alive(X, stats, tag, guards)


def make_input_map(map_rule: str, protocol_hash: str):
    graph = load_graph(load_neurons=False)
    nodes = H.select_nodes(graph, N_NODES)
    A, _ = induced_subgraph(graph, nodes)
    if map_rule == "top_positive_indegree":
        scores = [float((A.getcol(j).data > 0).sum()) for j in range(N_NODES)]
        ranked = sorted(range(N_NODES), key=lambda j: (-scores[j], j))
        rule = "top-50 local nodes by positive active incoming-edge count; ties by local index"
        selected = ranked[:N_INPUTS]
        score_key = "positive_indegree_top50"
    elif map_rule == "hash_ranked":
        ranked = sorted(
            range(N_NODES),
            key=lambda j: hashlib.sha256(f"{protocol_hash}|hash_ranked|{j}".encode()).digest(),
        )
        selected = ranked[:N_INPUTS]
        scores = [None] * N_NODES
        rule = "first 50 local nodes by deterministic protocol-hash rank; no graph metric"
        score_key = "hash_ranked_top50"
    else:
        raise ValueError(map_rule)
    inputs = np.sort(np.asarray(selected, dtype=np.int64))
    cue0 = np.asarray(selected[:INPUT_GROUP_SIZE], dtype=np.int64)
    cue1 = np.asarray(selected[INPUT_GROUP_SIZE:], dtype=np.int64)
    probe_seed = derive_seed(protocol_hash, "probe-map", map_rule) % (2**32)
    probes, _ = H.probe_set(N_NODES, inputs, N_PROBES, int(probe_seed))
    if np.intersect1d(inputs, probes).size:
        raise RuntimeError("input/probe leak")
    return inputs, cue0, cue1, probes, {
        "rule": rule,
        score_key: [
            {"local_node": int(j), "score": scores[j]} for j in selected
        ],
    }


def calibrate(variants, cfg, cue0, cue1, inputs, probes,
              protocol_hash: str, stage: str, seed: int, trials: int):
    base = dict(cfg["dynamics"]["lif"])
    lif0 = LIFParams(**base)
    amp = (lif0.v_th - lif0.v_rest) * lif0.tau_m / (lif0.r * lif0.dt)
    drive, _ = M.make_trials(
        N_NODES, cue0, cue1, trials, CALIBRATION_LAG, amp,
        protocol_hash, seed, f"{stage}-calibration",
    )
    gains = np.geomspace(GAIN_GRID_MIN, GAIN_GRID_MAX, GAIN_GRID_SIZE)
    calibrations = []
    for variant in variants:
        rho_abs = spectral_radius(variant["W"], signed=False)
        candidates = []
        for gain in gains:
            lif = LIFParams(**{
                **base,
                "syn_scale": syn_scale_for_gain(
                    rho_abs, float(gain), lif0.tau_m, lif0.dt, lif0.r
                ),
            })
            X, stats = simulate_terminal_features(
                variant["W"], drive, lif, inputs, probes,
                derive_seed(protocol_hash, "calibration-init", stage, seed, variant["name"]),
            )
            liveness = live_report(X, stats, f"{variant['name']}_calibration")
            denominator = len(drive) * drive.shape[1] * stats["pool_size"]
            rate = float(stats["pool_spikes"] / denominator) if denominator else 0.0
            candidates.append({
                "gain": float(gain), "syn_scale": float(lif.syn_scale),
                "rate": rate, "alive": bool(liveness["alive"]),
                "liveness": liveness,
            })
        calibrations.append({
            "name": variant["name"], "arm": variant["arm"],
            "replicate": variant["replicate"], "rho_abs": float(rho_abs),
            "candidates": candidates,
        })
    target, choice = M.common_rate_target(calibrations)
    selected = choice.get("selected", {})
    for item in calibrations:
        item["selected"] = selected.get(item["name"])
        item["relative_rate_error"] = (
            abs(item["selected"]["rate"] - target) / target
            if target and item["selected"] else None
        )
    return {
        "calibration_delay": CALIBRATION_LAG,
        "trials_per_class": int(trials),
        "gain_grid": {"min": GAIN_GRID_MIN, "max": GAIN_GRID_MAX, "points": GAIN_GRID_SIZE},
        "common_target_rate": target,
        "primary_rate_match_ok": bool(choice.get("primary_rate_match_ok", False)),
        "primary_max_relative_error": choice.get("primary_max_relative_error"),
        "variants": calibrations,
    }


def run_cell(variants, calibration, cfg, inputs, cue0, cue1, probes,
             protocol_hash: str, runner_hash: str, stage: str, seed: int,
             lag: int, trials: int):
    base = dict(cfg["dynamics"]["lif"])
    lif0 = LIFParams(**base)
    amp = (lif0.v_th - lif0.v_rest) * lif0.tau_m / (lif0.r * lif0.dt)
    train_drive, ytr = M.make_trials(
        N_NODES, cue0, cue1, trials, lag, amp, protocol_hash, seed, f"{stage}-train",
    )
    test_drive, yte = M.make_trials(
        N_NODES, cue0, cue1, trials, lag, amp, protocol_hash, seed, f"{stage}-test",
    )
    target = calibration["common_target_rate"]
    results = {}
    started = time.perf_counter()
    for variant in variants:
        selected = next(
            item["selected"] for item in calibration["variants"]
            if item["name"] == variant["name"]
        )
        base_row = {
            "arm": variant["arm"], "replicate": variant["replicate"],
            "gain": selected["gain"] if selected else None,
            "syn_scale": selected["syn_scale"] if selected else None,
            "active_edges": int(variant["W"].nnz), "accuracy": None,
        }
        if selected is None or target is None:
            base_row.update({"status": "MISSING", "alive": False, "rate_match": False,
                             "reason": "no primary common calibration target"})
            results[variant["name"]] = base_row
            continue
        lif = LIFParams(**{**base, "syn_scale": selected["syn_scale"]})
        t0 = time.perf_counter()
        Xtr, sttr = simulate_terminal_features(
            variant["W"], train_drive, lif, inputs, probes,
            derive_seed(protocol_hash, "sim-init", stage, seed, lag, variant["name"], "train"),
        )
        Xte, stte = simulate_terminal_features(
            variant["W"], test_drive, lif, inputs, probes,
            derive_seed(protocol_hash, "sim-init", stage, seed, lag, variant["name"], "test"),
        )
        tr_live = live_report(Xtr, sttr, f"{variant['name']}_train")
        te_live = live_report(Xte, stte, f"{variant['name']}_test")
        combined = live_report(
            np.concatenate([Xtr, Xte]),
            {"pool_spikes": sttr["pool_spikes"] + stte["pool_spikes"],
             "probe_spikes": sttr["probe_spikes"] + stte["probe_spikes"],
             "pool_size": sttr["pool_size"]},
            variant["name"],
        )
        liveness = M.combine_split_liveness(combined, tr_live, te_live)
        denom_tr = len(train_drive) * (lag + 1) * sttr["pool_size"]
        denom_te = len(test_drive) * (lag + 1) * stte["pool_size"]
        train_rate = float(sttr["pool_spikes"] / denom_tr) if denom_tr else 0.0
        test_rate = float(stte["pool_spikes"] / denom_te) if denom_te else 0.0
        train_err = abs(train_rate - target) / target
        test_err = abs(test_rate - target) / target
        rate_match = bool(train_err <= RATE_MATCH_TOL and test_err <= RATE_MATCH_TOL)
        alive = bool(liveness["alive"])
        status = "LIVE" if alive and rate_match else "MISSING"
        reason = []
        if not alive:
            reason.append(liveness.get("dead_reason", "liveness guard failed"))
        if not rate_match:
            reason.append("train/test rate outside preregistered band")
        scored = M.fit_ridge_train_only(
            Xtr, ytr, Xte, yte, protocol_hash, stage, seed, lag
        ) if status == "LIVE" else None
        base_row.update({
            "status": status, "alive": alive, "rate_match": rate_match,
            "liveness": liveness, "train_rate": train_rate, "test_rate": test_rate,
            "train_relative_rate_error": float(train_err),
            "test_relative_rate_error": float(test_err),
            "calibration_rate": float(selected["rate"]),
            "accuracy": scored["accuracy"] if scored else None,
            "train_accuracy": scored["train_accuracy"] if scored else None,
            "validation_accuracy": scored["validation_accuracy"] if scored else None,
            "selected_ridge": scored["selected_ridge"] if scored else None,
            "test_predictions": scored["test_predictions"] if scored else None,
            "reason": "; ".join(reason) if reason else None,
            "wall_seconds": time.perf_counter() - t0,
            "synapse_step_ops": int(variant["W"].nnz * (lag + 1) * (len(ytr) + len(yte))),
        })
        results[variant["name"]] = base_row
    return {
        "experiment_id": EXPERIMENT_ID, "stage": stage, "seed": int(seed),
        "lag_steps": int(lag), "trials_per_class_per_split": int(trials),
        "input_ids": inputs.tolist(), "cue0": cue0.tolist(), "cue1": cue1.tolist(),
        "probe_ids": probes.tolist(), "results": results,
        "labels_test": yte.astype(int).tolist(),
        "cell_wall_seconds": time.perf_counter() - started,
        "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
    }


def interval(values):
    x = np.asarray(values, dtype=float)
    if len(x) < 2:
        return {"n": int(len(x)), "mean": float(x.mean()) if len(x) else None,
                "ci95_low": None, "ci95_high": None}
    mean = float(x.mean())
    half = float(t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)))
    return {"n": int(len(x)), "mean": mean, "ci95_low": mean - half, "ci95_high": mean + half}


def aggregate(stage_dir, seeds, delays, protocol_hash, runner_hash):
    cells = []
    for seed in seeds:
        for lag in delays:
            path = stage_dir / f"seed_{seed:04d}_lag_{lag:03d}.json"
            if path.exists():
                cells.append(read_checkpoint(path, protocol_hash, runner_hash))
    curve = {}
    paired_by_delay = {}
    for lag in delays:
        rows = [c for c in cells if c["lag_steps"] == lag]
        pairs = []
        for row in rows:
            c = row["results"].get("connectome-0", {})
            d = row["results"].get("dp-0", {})
            if c.get("status") == "LIVE" and d.get("status") == "LIVE":
                pairs.append({"seed": row["seed"], "connectome": c["accuracy"], "dp": d["accuracy"],
                              "difference": float(c["accuracy"] - d["accuracy"])})
        paired_by_delay[str(lag)] = pairs
        curve[str(lag)] = {
            "eligible": bool(pairs),
            "connectome": interval([p["connectome"] for p in pairs]),
            "dp": interval([p["dp"] for p in pairs]),
            "paired_difference_connectome_minus_dp": interval([p["difference"] for p in pairs]),
            "by_seed": pairs,
        }
    eligible_delays = [lag for lag in delays if paired_by_delay[str(lag)]]
    if len(eligible_delays) >= 3:
        curve_status = "INTERPRETABLE"
    elif not eligible_delays:
        curve_status = "NO_PAIR"
    else:
        curve_status = "INCONCLUSIVE"
    return {
        "experiment_id": EXPERIMENT_ID, "stage": stage_dir.name,
        "curve_status": curve_status, "scientific_result": bool(eligible_delays),
        "n_seeds": len(seeds), "delays": list(delays), "arms": list(ARM_TYPES),
        "cells_written": len(cells), "expected_cells": len(seeds) * len(delays),
        "eligible_delays": eligible_delays, "curve": curve,
        "secondary_missing_does_not_gate_primary": True,
        "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
    }


def make_run_root(map_rule):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rev = H.provenance().get("git_rev", "unknown")
    root = RESULTS / f"mem003_{stamp}_{rev}_{map_rule}"
    root.mkdir(parents=True)
    return root


def check_run_root(path: Path):
    resolved = path.resolve()
    allowed = RESULTS.resolve()
    if allowed not in resolved.parents or not resolved.name.startswith("mem003_"):
        raise ValueError(f"run root must be a mem003_* directory below {allowed}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def run(stage: str, run_root: Path, map_rule: str):
    cfg = H.load_cfg()
    protocol_hash = sha256_file(PROTOCOL)
    runner_hash = sha256_file(Path(__file__))
    run_root = check_run_root(run_root)
    stage_dir = run_root / stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    if stage == "smoke":
        seeds, delays, trials, cal_trials = SMOKE_SEEDS, SMOKE_DELAYS, SMOKE_TRIALS_PER_CLASS, SMOKE_CALIBRATION_TRIALS_PER_CLASS
    elif stage == "curve":
        seeds, delays, trials, cal_trials = SEEDS, DELAYS, TRIALS_PER_CLASS, CALIBRATION_TRIALS_PER_CLASS
    else:
        raise ValueError(stage)
    graph = load_graph(load_neurons=False)
    nodes = H.select_nodes(graph, N_NODES)
    inputs, cue0, cue1, probes, map_meta = make_input_map(map_rule, protocol_hash)
    graph_sha = {name: sha256_file(ROOT / "data/derived/graph" / name)
                 for name in ("csr_unsigned.npz", "csc_unsigned.npz", "coo_signed.npz")}
    cfg_hash = sha256_file(H.CFG_PATH)
    start_path = stage_dir / "stage_started.json"
    if not start_path.exists():
        write_json_once(start_path, {
            "experiment_id": EXPERIMENT_ID, "stage": stage,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
            "config_sha256": cfg_hash, "graph_sha256": graph_sha,
            "input_map": map_meta, "map_rule": map_rule,
            "input_ids": inputs.tolist(), "cue0": cue0.tolist(),
            "cue1": cue1.tolist(), "probe_ids": probes.tolist(),
            "arms": list(ARM_TYPES), "delays": list(delays), "seeds": list(seeds),
        })
    for seed in seeds:
        variants, graph_diag = M.create_graph_variants(graph, nodes, protocol_hash, seed, replicates=1)
        cal_path = stage_dir / f"calibration_seed_{seed:04d}.json"
        cal = read_checkpoint(cal_path, protocol_hash, runner_hash)
        if cal is None:
            cal = calibrate(variants, cfg, cue0, cue1, inputs, probes,
                            protocol_hash, stage, seed, cal_trials)
            write_json_once(cal_path, {
                "experiment_id": EXPERIMENT_ID, "stage": stage, "seed": int(seed),
                "map_rule": map_rule, "input_map": map_meta,
                "graph_diagnostics": graph_diag, **cal,
                "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
            })
        for lag in delays:
            cell_path = stage_dir / f"seed_{seed:04d}_lag_{lag:03d}.json"
            if read_checkpoint(cell_path, protocol_hash, runner_hash) is not None:
                continue
            row = run_cell(variants, cal, cfg, inputs, cue0, cue1, probes,
                           protocol_hash, runner_hash, stage, seed, lag, trials)
            row.update({"graph_diagnostics": graph_diag, "graph_sha256": graph_sha,
                        "config_sha256": cfg_hash, "map_rule": map_rule})
            write_json_once(cell_path, row)
            print(json.dumps({
                "stage": stage, "seed": seed, "delay": lag,
                "status": {name: item["status"] for name, item in row["results"].items()},
                "primary_pair": row["results"]["connectome-0"]["status"] == "LIVE"
                and row["results"]["dp-0"]["status"] == "LIVE",
                "wall_s": round(row["cell_wall_seconds"], 2),
            }), flush=True)
    summary = aggregate(stage_dir, seeds, delays, protocol_hash, runner_hash)
    summary_path = stage_dir / "summary.json"
    if not summary_path.exists():
        write_json_once(summary_path, summary)
    print(json.dumps({
        "run_root": str(run_root), "stage": stage,
        "curve_status": summary["curve_status"],
        "eligible_delays": summary["eligible_delays"],
        "cells_written": summary["cells_written"],
        "summary": str(summary_path.relative_to(ROOT)),
    }, indent=2), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "curve"), required=True)
    parser.add_argument("--map", choices=("top_positive_indegree", "hash_ranked"),
                        default="top_positive_indegree")
    parser.add_argument("--run-root", type=Path)
    args = parser.parse_args(argv)
    if not PROTOCOL.is_file():
        parser.error(f"missing frozen preregistration: {PROTOCOL}")
    run(args.stage, args.run_root or make_run_root(args.map), args.map)


if __name__ == "__main__":
    main()
