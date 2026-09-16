"""EXP-MEM-002: accuracy-blind liveness/rate instrument check."""
from __future__ import annotations

import argparse
import contextlib
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
from memory_task import combine_split_liveness, simulate_terminal_features

EXPERIMENT_ID = "EXP-MEM-002"
PROTOCOL = ROOT / "experiments/results/EXP-MEM-002/protocol.md"
PROTOCOL_MAP2 = ROOT / "experiments/results/EXP-MEM-002/protocol_map2.md"
RESULTS = ROOT / "experiments/results/EXP-MEM-002"
DELAYS = (10, 25, 50, 100, 250, 500)  # SOURCE: frozen protocol.md
SMOKE_DELAYS = (10, 100)  # SOURCE: frozen protocol.md smoke plan
SEEDS = tuple(range(12))  # SOURCE: frozen protocol.md
SMOKE_SEEDS = (0,)  # SOURCE: frozen protocol.md smoke plan
N_NODES = 500  # SOURCE: frozen protocol.md
N_INPUTS = 50  # SOURCE: frozen protocol.md, 10% of n=500
INPUT_GROUP_SIZE = 25  # SOURCE: frozen protocol.md, balanced cue groups
N_PROBES = 48  # SOURCE: frozen protocol.md
CALIBRATION_LAG = 100  # SOURCE: frozen protocol.md
TRIALS_PER_CLASS = 10  # SOURCE: frozen protocol.md
SMOKE_TRIALS_PER_CLASS = 2  # SOURCE: frozen protocol.md smoke plan
CALIBRATION_TRIALS_PER_CLASS = 10  # SOURCE: frozen protocol.md
SMOKE_CALIBRATION_TRIALS_PER_CLASS = 2  # SOURCE: frozen protocol.md smoke plan
GAIN_GRID_MIN = 0.125  # GUESS: preregistered gain-cap lower bound; calibrate with live data later
GAIN_GRID_MAX = 64.0  # GUESS: preregistered gain-cap upper bound; calibrate with live data later
GAIN_GRID_SIZE = 64  # GUESS: preregistered calibration resolution
RATE_MATCH_TOL = 0.10  # GUESS: preregistered instrument tolerance; needs calibration data
LIVENESS_MIN_UNIQUE = 2  # SOURCE: existing harness guard used by EXP-MEM-001
ARM_TYPES = ("connectome", "dp", "weight_perm", "er", "ring")


def sha256_file(path: Path) -> str:
    return M.sha256_file(path)


def write_json_once(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if path.exists() or tmp.exists():
        raise FileExistsError(f"refusing to overwrite artifact/checkpoint: {path}")
    with tmp.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
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


def make_input_map(n: int, protocol_hash: str, map_rule: str):
    """Build one of the two preregistered accuracy-blind input maps."""
    graph = load_graph(load_neurons=False)
    nodes = H.select_nodes(graph, n)
    A, _ = induced_subgraph(graph, nodes)
    if map_rule == "top_positive_outdegree":
        scores = [float((A.getrow(j).data > 0).sum()) for j in range(n)]
        rule = "top-50 local nodes by positive active outgoing-edge count; ties by local index; alternate cue groups"
    elif map_rule == "top_positive_weight_sum":
        scores = [float(A.getrow(j).data[A.getrow(j).data > 0].sum()) for j in range(n)]
        rule = "top-50 local nodes by positive active outgoing-weight sum; ties by local index; alternate cue groups"
    else:
        raise ValueError(map_rule)
    ranked = sorted(range(n), key=lambda j: (-scores[j], j))
    selected = ranked[:N_INPUTS]
    inputs = np.sort(np.asarray(selected, dtype=np.int64))
    cue0 = np.asarray(selected[::2], dtype=np.int64)
    cue1 = np.asarray(selected[1::2], dtype=np.int64)
    probe_seed = M.derive_seed(protocol_hash, "probe-map", map_rule) % (2**32)
    probes, _ = H.probe_set(n, inputs, N_PROBES, int(probe_seed))
    if np.intersect1d(inputs, probes).size:
        raise RuntimeError("input/probe leak")
    return inputs, cue0, cue1, probes, {
        "rule": rule,
        "positive_outdegree_top50": [
            {"local_node": int(j), "score": scores[j]}
            for j in selected
        ],
    }


def live_report(X, stats, tag):
    guards = dict(H.load_cfg().get("harness_guards", {}))
    guards.update({"on_dead": "record", "min_unique_feature_rows": LIVENESS_MIN_UNIQUE})
    with contextlib.redirect_stdout(io.StringIO()):
        return H.check_alive(X, stats, tag, guards)


def rate(stats, n_trials, lag):
    denominator = int(n_trials) * (int(lag) + 1) * int(stats["pool_size"])
    return float(stats["pool_spikes"] / denominator) if denominator else 0.0


def calibration_target(calibrations):
    """Choose a common target using all five arms, before delay outcomes."""
    live = {
        item["name"]: [c for c in item["candidates"] if c["alive"] and c["rate"] > 0]
        for item in calibrations
    }
    if any(not candidates for candidates in live.values()):
        return None, {"status": "MISSING_ARM_HAS_NO_LIVE_POSITIVE_CANDIDATE"}
    targets = sorted({float(c["rate"]) for candidates in live.values() for c in candidates})

    def errors(target):
        return [
            min(abs(c["rate"] - target) / target for c in candidates)
            for candidates in live.values()
        ]

    target = min(targets, key=lambda value: (max(errors(value)), np.mean(errors(value)), value))
    selected = {}
    for item in calibrations:
        candidates = live[item["name"]]
        selected[item["name"]] = min(candidates, key=lambda c: (abs(c["rate"] - target) / target, c["gain"]))
    rel_errors = {name: abs(c["rate"] - target) / target for name, c in selected.items()}
    return float(target), {
        "status": "TARGET_SELECTED",
        "selected": selected,
        "relative_errors": rel_errors,
        "all_arms_rate_match": bool(all(error <= RATE_MATCH_TOL for error in rel_errors.values())),
        "worst_relative_error": float(max(rel_errors.values())),
    }


def calibrate(variants, cfg, inputs, cue0, cue1, probes, protocol_hash, stage, seed, trials):
    base = dict(cfg["dynamics"]["lif"])
    lif0 = LIFParams(**base)
    cue_amp = (lif0.v_th - lif0.v_rest) * lif0.tau_m / (lif0.r * lif0.dt)
    gains = np.geomspace(GAIN_GRID_MIN, GAIN_GRID_MAX, GAIN_GRID_SIZE)
    result = []
    for variant in variants:
        W = variant["W"]
        rho_abs = spectral_radius(W, signed=False)
        candidates = []
        for gain in gains:
            lif = LIFParams(**{
                **base,
                "syn_scale": syn_scale_for_gain(rho_abs, float(gain), lif0.tau_m, lif0.dt, lif0.r),
            })
            train_drive, _ = M.make_trials(
                N_NODES, cue0, cue1, trials, CALIBRATION_LAG, cue_amp,
                protocol_hash, seed, f"{stage}-calibration-train",
            )
            test_drive, _ = M.make_trials(
                N_NODES, cue0, cue1, trials, CALIBRATION_LAG, cue_amp,
                protocol_hash, seed, f"{stage}-calibration-test",
            )
            Xtr, sttr = simulate_terminal_features(
                W, train_drive, lif, inputs, probes,
                M.derive_seed(protocol_hash, "calibration-init", stage, seed, variant["name"], "train"),
            )
            Xte, stte = simulate_terminal_features(
                W, test_drive, lif, inputs, probes,
                M.derive_seed(protocol_hash, "calibration-init", stage, seed, variant["name"], "test"),
            )
            tr_live = live_report(Xtr, sttr, f"{variant['name']}_calibration_train")
            te_live = live_report(Xte, stte, f"{variant['name']}_calibration_test")
            combined_stats = {
                "pool_spikes": sttr["pool_spikes"] + stte["pool_spikes"],
                "probe_spikes": sttr["probe_spikes"] + stte["probe_spikes"],
                "pool_size": sttr["pool_size"],
            }
            combined = live_report(np.concatenate([Xtr, Xte]), combined_stats, variant["name"])
            split = combine_split_liveness(combined, tr_live, te_live)
            candidates.append({
                "gain": float(gain),
                "syn_scale": float(lif.syn_scale),
                "train_rate": rate(sttr, len(train_drive), CALIBRATION_LAG),
                "test_rate": rate(stte, len(test_drive), CALIBRATION_LAG),
                "rate": float((sttr["pool_spikes"] + stte["pool_spikes"]) /
                              ((len(train_drive) + len(test_drive)) * (CALIBRATION_LAG + 1) * sttr["pool_size"])),
                "alive": bool(split["alive"]),
                "liveness": split,
            })
        result.append({
            "name": variant["name"], "arm": variant["arm"], "replicate": variant["replicate"],
            "rho_abs": float(rho_abs), "candidates": candidates,
        })
    target, choice = calibration_target(result)
    for item in result:
        item["selected"] = choice.get("selected", {}).get(item["name"])
    return {
        "calibration_delay": CALIBRATION_LAG,
        "trials_per_class_per_split": int(trials),
        "gain_grid": {"min": GAIN_GRID_MIN, "max": GAIN_GRID_MAX, "points": GAIN_GRID_SIZE},
        "target_rate": target,
        "target_selection": choice,
        "variants": result,
    }


def run_cell(variants, calibration, cfg, inputs, cue0, cue1, probes,
             protocol_hash, runner_hash, stage, seed, lag, trials):
    base = dict(cfg["dynamics"]["lif"])
    lif0 = LIFParams(**base)
    cue_amp = (lif0.v_th - lif0.v_rest) * lif0.tau_m / (lif0.r * lif0.dt)
    train_drive, _ = M.make_trials(N_NODES, cue0, cue1, trials, lag, cue_amp,
                                   protocol_hash, seed, f"{stage}-train")
    test_drive, _ = M.make_trials(N_NODES, cue0, cue1, trials, lag, cue_amp,
                                  protocol_hash, seed, f"{stage}-test")
    target = calibration["target_rate"]
    rows = {}
    started = time.perf_counter()
    for variant in variants:
        selected = next(item["selected"] for item in calibration["variants"]
                        if item["name"] == variant["name"])
        if selected is None or target is None:
            rows[variant["name"]] = {
                "arm": variant["arm"], "replicate": variant["replicate"],
                "status": "MISSING", "alive": False, "rate_match": False,
                "reason": "no common live calibration target across all arms",
                "gain": selected["gain"] if selected else None,
            }
            continue
        lif = LIFParams(**{**base, "syn_scale": selected["syn_scale"]})
        t0, c0 = time.perf_counter(), time.process_time()
        Xtr, sttr = simulate_terminal_features(
            variant["W"], train_drive, lif, inputs, probes,
            M.derive_seed(protocol_hash, "sim-init", stage, seed, lag, variant["name"], "train"),
        )
        Xte, stte = simulate_terminal_features(
            variant["W"], test_drive, lif, inputs, probes,
            M.derive_seed(protocol_hash, "sim-init", stage, seed, lag, variant["name"], "test"),
        )
        tr_live = live_report(Xtr, sttr, f"{variant['name']}_train")
        te_live = live_report(Xte, stte, f"{variant['name']}_test")
        combined_stats = {
            "pool_spikes": sttr["pool_spikes"] + stte["pool_spikes"],
            "probe_spikes": sttr["probe_spikes"] + stte["probe_spikes"],
            "pool_size": sttr["pool_size"],
        }
        combined = live_report(np.concatenate([Xtr, Xte]), combined_stats, variant["name"])
        liveness = combine_split_liveness(combined, tr_live, te_live)
        train_rate = rate(sttr, len(train_drive), lag)
        test_rate = rate(stte, len(test_drive), lag)
        train_error = abs(train_rate - target) / target
        test_error = abs(test_rate - target) / target
        rate_match = bool(train_error <= RATE_MATCH_TOL and test_error <= RATE_MATCH_TOL)
        status = "LIVE" if liveness["alive"] and rate_match else "MISSING"
        reasons = []
        if not liveness["alive"]:
            reasons.append(liveness.get("dead_reason", "liveness guard failed"))
        if not rate_match:
            reasons.append("train/test realised rate outside preregistered tolerance")
        rows[variant["name"]] = {
            "arm": variant["arm"], "replicate": variant["replicate"], "status": status,
            "alive": bool(liveness["alive"]), "rate_match": rate_match,
            "liveness": liveness, "train_rate": train_rate, "test_rate": test_rate,
            "train_relative_rate_error": train_error, "test_relative_rate_error": test_error,
            "target_rate": target, "gain": selected["gain"], "syn_scale": selected["syn_scale"],
            "active_edges": int(variant["W"].nnz),
            "reason": "; ".join(reasons) if reasons else None,
            "wall_seconds": time.perf_counter() - t0,
            "cpu_seconds": time.process_time() - c0,
        }
    return {
        "experiment_id": EXPERIMENT_ID, "stage": stage, "seed": int(seed), "lag_steps": int(lag),
        "trials_per_class_per_split": int(trials),
        "input_ids": inputs.tolist(), "cue0": cue0.tolist(), "cue1": cue1.tolist(),
        "probe_ids": probes.tolist(), "cue_amplitude": float(cue_amp),
        "external_input_after_onset_nonzero_count": int(np.count_nonzero(test_drive[:, 1:, :])),
        "results": rows, "cell_wall_seconds": time.perf_counter() - started,
        "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
    }


def aggregate(stage_dir, seeds, delays, protocol_hash, runner_hash):
    cells = []
    for seed in seeds:
        for lag in delays:
            path = stage_dir / f"seed_{seed:04d}_lag_{lag:03d}.json"
            if path.exists():
                cells.append(read_checkpoint(path, protocol_hash, runner_hash))
    complete_delays = []
    by_delay = {}
    missing_cells = []
    for lag in delays:
        rows = [cell for cell in cells if cell["lag_steps"] == lag]
        complete = len(rows) == len(seeds) and all(
            len(cell["results"]) == len(ARM_TYPES)
            and all(item["status"] == "LIVE" for item in cell["results"].values())
            for cell in rows
        )
        if complete:
            complete_delays.append(lag)
        by_delay[str(lag)] = {"cells": len(rows), "expected_cells": len(seeds), "complete": complete}
        for cell in rows:
            for name, item in cell["results"].items():
                if item["status"] != "LIVE":
                    missing_cells.append({"seed": cell["seed"], "delay": lag, "variant": name,
                                          "arm": item["arm"], "reason": item.get("reason")})
    expected = len(seeds) * len(delays)
    status = "INSTRUMENT_COMPLETE" if len(cells) == expected and len(complete_delays) == len(delays) else "INSTRUMENT_INCOMPLETE"
    return {
        "experiment_id": EXPERIMENT_ID, "status": status, "scientific_result": False,
        "n_seeds": len(seeds), "delays": list(delays), "arms": list(ARM_TYPES),
        "cells_written": len(cells), "expected_cells": expected,
        "complete_delays": complete_delays, "by_delay": by_delay,
        "missing_cells": missing_cells, "no_accuracy_or_auc_computed": True,
        "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
    }


def make_run_root():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rev = H.provenance().get("git_rev", "unknown")
    root = RESULTS / f"q0_{stamp}_{rev}"
    suffix = 0
    candidate = root
    while candidate.exists():
        suffix += 1
        candidate = RESULTS / f"q0_{stamp}_{rev}_{suffix}"
    candidate.mkdir(parents=True)
    return candidate


def check_run_root(path: Path):
    resolved = path.resolve()
    allowed = RESULTS.resolve()
    if allowed not in resolved.parents or not resolved.name.startswith("q0_"):
        raise ValueError(f"run root must be a q0_* directory below {allowed}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def run(stage: str, run_root: Path, cfg: dict, map_rule: str):
    protocol_path = PROTOCOL if map_rule == "top_positive_outdegree" else PROTOCOL_MAP2
    protocol_hash = sha256_file(protocol_path)
    runner_hash = sha256_file(Path(__file__))
    run_root = check_run_root(run_root)
    stage_dir = run_root / stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    if stage == "smoke":
        seeds, delays, trials, cal_trials = SMOKE_SEEDS, SMOKE_DELAYS, SMOKE_TRIALS_PER_CLASS, SMOKE_CALIBRATION_TRIALS_PER_CLASS
    elif stage == "q0":
        seeds, delays, trials, cal_trials = SEEDS, DELAYS, TRIALS_PER_CLASS, CALIBRATION_TRIALS_PER_CLASS
    else:
        raise ValueError(stage)
    graph = load_graph(load_neurons=False)
    nodes = H.select_nodes(graph, N_NODES)
    graph_sha = {name: sha256_file(ROOT / "data/derived/graph" / name)
                 for name in ("csr_unsigned.npz", "csc_unsigned.npz", "coo_signed.npz")}
    cfg_hash = sha256_file(H.CFG_PATH)
    inputs, cue0, cue1, probes, map_meta = make_input_map(N_NODES, protocol_hash, map_rule)
    start_path = stage_dir / "stage_started.json"
    if not start_path.exists():
        write_json_once(start_path, {
            "experiment_id": EXPERIMENT_ID, "stage": stage,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
            "config_sha256": cfg_hash, "graph_sha256": graph_sha,
            "protocol_path": str(protocol_path.relative_to(ROOT)), "input_map": map_meta,
            "input_ids": inputs.tolist(), "cue0": cue0.tolist(),
            "cue1": cue1.tolist(), "probe_ids": probes.tolist(),
            "arms": list(ARM_TYPES), "delays": list(delays), "seeds": list(seeds),
        })
    for seed in seeds:
        variants, graph_diag = M.create_graph_variants(graph, nodes, protocol_hash, seed, replicates=1)
        cal_path = stage_dir / f"calibration_seed_{seed:04d}.json"
        caldata = read_checkpoint(cal_path, protocol_hash, runner_hash)
        if caldata is None:
            cal = calibrate(variants, cfg, inputs, cue0, cue1, probes, protocol_hash, stage, seed, cal_trials)
            caldata = {
                "experiment_id": EXPERIMENT_ID, "stage": stage, "seed": int(seed),
                "input_ids": inputs.tolist(), "cue0": cue0.tolist(), "cue1": cue1.tolist(),
                "probe_ids": probes.tolist(), "graph_diagnostics": graph_diag,
                "map_rule": map_meta["rule"], **cal,
                "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
            }
            write_json_once(cal_path, caldata)
        for lag in delays:
            cell_path = stage_dir / f"seed_{seed:04d}_lag_{lag:03d}.json"
            if read_checkpoint(cell_path, protocol_hash, runner_hash) is not None:
                continue
            row = run_cell(variants, caldata, cfg, inputs, cue0, cue1, probes,
                           protocol_hash, runner_hash, stage, seed, lag, trials)
            row["graph_diagnostics"] = graph_diag
            row["graph_sha256"] = graph_sha
            row["config_sha256"] = cfg_hash
            row["map_rule"] = map_meta["rule"]
            write_json_once(cell_path, row)
            print(json.dumps({
                "stage": stage, "seed": seed, "delay": lag,
                "status": {name: item["status"] for name, item in row["results"].items()},
                "target_rate": caldata["target_rate"],
                "wall_s": round(row["cell_wall_seconds"], 2),
            }), flush=True)
    summary = aggregate(stage_dir, seeds, delays, protocol_hash, runner_hash)
    summary_path = stage_dir / "summary.json"
    if not summary_path.exists():
        write_json_once(summary_path, summary)
    complete_path = stage_dir / "stage_complete.json"
    if not complete_path.exists():
        write_json_once(complete_path, {
            "experiment_id": EXPERIMENT_ID, "stage": stage,
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "status": summary["status"], "summary_path": str(summary_path.relative_to(ROOT)),
            "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
        })
    print(json.dumps({"run_root": str(run_root), "stage": stage,
                      "status": summary["status"], "summary": str(summary_path.relative_to(ROOT)),
                      "complete_delays": summary["complete_delays"],
                      "cells_written": summary["cells_written"]}, indent=2), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "q0"), required=True)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--map", choices=("top_positive_outdegree", "top_positive_weight_sum"),
                        default="top_positive_outdegree")
    args = parser.parse_args(argv)
    protocol = PROTOCOL if args.map == "top_positive_outdegree" else PROTOCOL_MAP2
    if not protocol.is_file():
        parser.error(f"missing frozen preregistration: {protocol}")
    run(args.stage, args.run_root or make_run_root(), H.load_cfg(), args.map)


if __name__ == "__main__":
    main()
