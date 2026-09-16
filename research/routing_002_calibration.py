#!/usr/bin/env python3
"""ROUTING-002: fixed gain-envelope calibration, no task metric."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "harness"))

import routing_001 as R


# SOURCE: fixed grid in ROUTING-002-PROTOCOL.md.
GAIN_POINTS = 9
# SOURCE: fixed target/tolerance reference in ROUTING-002-PROTOCOL.md.
TARGET_RATE = R.TARGET_RATE
REL_TOL = R.GAIN_REL_TOL
# SOURCE: fixed calibration-trial count inherited from ROUTING-001.
CAL_TRIALS = 8
# SOURCE: campaign requirement and ROUTING-001 protocol.
SEEDS = tuple(range(12))
ARMS = ("connectome_signed", "degree_preserving", "block_preserving")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def pool_rate(W, spec, currents, streams, seed, gain):
    lif = R.lif_for_gain(W, spec, float(gain))
    _, stats = R.simulate_features(
        W, currents, lif, int(seed), streams["input_ids"], streams["probe_ids"]
    )
    pool_size = W.shape[0] - len(streams["input_ids"])
    denominator = len(currents) * R.N_STEPS * pool_size
    spikes = float(stats["pool_spikes"].sum())
    return {
        "gain": float(gain),
        "syn_scale": float(lif.syn_scale),
        "pool_spikes": spikes,
        "pool_size": int(pool_size),
        "steps": int(len(currents) * R.N_STEPS),
        "rate": float(spikes / denominator),
    }


def run_seed(g, nodes, labels, streams, seed: int, outdir: Path) -> dict:
    started = time.perf_counter()
    arms, diagnostics = R.build_graph_arms(g, nodes, labels, int(seed))
    currents = R.make_calibration(len(nodes), streams, int(seed))
    gains = np.geomspace(R.GAIN_LO, R.GAIN_HI, GAIN_POINTS)
    arm_results = {}
    for name in ARMS:
        W = arms[name]
        spec = R.arm_spectrum(W)
        curve = [pool_rate(W, spec, currents, streams, seed, gain) for gain in gains]
        reachable = [
            row for row in curve
            if abs(row["rate"] - TARGET_RATE) <= REL_TOL * TARGET_RATE
        ]
        arm_results[name] = {
            "spectrum": spec,
            "curve": curve,
            "target_rate": TARGET_RATE,
            "relative_tolerance": REL_TOL,
            "target_reachable_on_grid": bool(reachable),
            "closest_grid_rate": min(
                (row["rate"] for row in curve),
                key=lambda x: abs(x - TARGET_RATE),
            ),
        }
    result = {
        "experiment": "ROUTING-002",
        "status": "MEASURED",
        "seed": int(seed),
        "started_utc": utc_now(),
        "selected_labels": streams["selected_labels"],
        "source_edge_count": int(diagnostics["source_edges"]),
        "arm_diagnostics": diagnostics,
        "gain_grid": [float(x) for x in gains],
        "arms": arm_results,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    R.write_json_once(outdir / ("seed-%02d.json" % seed), result)
    return result


def aggregate(results: list[dict]) -> dict:
    out = {"experiment": "ROUTING-002", "classification": "CALIBRATION_ONLY",
           "arms": {}, "seeds_completed": [int(r["seed"]) for r in results]}
    for name in ARMS:
        rows = [r["arms"][name] for r in results]
        reach = [bool(r["target_reachable_on_grid"]) for r in rows]
        max_rates = [max(x["rate"] for x in r["curve"]) for r in rows]
        min_errors = [
            min(abs(x["rate"] - TARGET_RATE) for x in r["curve"]) for r in rows
        ]
        out["arms"][name] = {
            "n_seeds": len(rows),
            "target_reachable_count": int(sum(reach)),
            "target_reachable_by_seed": reach,
            "mean_max_grid_rate": float(np.mean(max_rates)),
            "mean_closest_absolute_rate_error": float(np.mean(min_errors)),
        }
    return out


def main() -> None:
    started = time.perf_counter()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root_out = ROOT / "research" / "results" / "ROUTING-002"
    outdir = root_out / ("FULL_" + stamp + "_" + R.git_rev()[:12])
    suffix = 1
    while outdir.exists():
        outdir = root_out / ("FULL_" + stamp + "_" + R.git_rev()[:12] + "_" + str(suffix))
        suffix += 1
    outdir.mkdir(parents=True)
    g = R.load_graph(load_neurons=False)
    labels = R.load_superclasses()
    nodes, degree = R.choose_nodes(g)
    streams = R.choose_streams(nodes, degree, labels)
    protocol = ROOT / "research" / "ROUTING-002-PROTOCOL.md"
    meta = {
        "experiment": "ROUTING-002",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "git_tip": R.git_rev(),
        "protocol_sha256": R.sha256_file(protocol),
        "routing_001_code_sha256": R.sha256_file(ROOT / "research" / "routing_001.py"),
        "graph_meta_sha256": R.sha256_file(ROOT / "data" / "derived" / "graph" / "graph_meta.json"),
        "neurons_sha256": R.sha256_file(ROOT / "data" / "derived" / "graph" / "neurons.feather"),
        "gain_grid": [float(x) for x in np.geomspace(R.GAIN_LO, R.GAIN_HI, GAIN_POINTS)],
        "target_rate": TARGET_RATE,
        "relative_tolerance": REL_TOL,
        "selected_labels": streams["selected_labels"],
        "selected_nodes": nodes,
        "selected_streams": streams,
        "raw_and_derived_graph_untouched": True,
        "output_dir": str(outdir),
    }
    R.write_json_once(outdir / "metadata.json", meta)
    print(json.dumps({"outdir": str(outdir), "gain_grid": meta["gain_grid"],
                      "selected_labels": streams["selected_labels"]}, sort_keys=True),
          flush=True)
    results = []
    for seed in SEEDS:
        print("seed", int(seed), flush=True)
        results.append(run_seed(g, nodes, labels, streams, int(seed), outdir))
    final = {
        "experiment": "ROUTING-002",
        "status": "COMPLETE",
        "started_utc": meta["started_utc"],
        "finished_utc": utc_now(),
        "results_dir": str(outdir),
        "aggregate": aggregate(results),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    R.write_json_once(outdir / "summary.json", final)
    print(json.dumps(final["aggregate"], indent=2, sort_keys=True), flush=True)
    print("WROTE", outdir / "summary.json", flush=True)


if __name__ == "__main__":
    main()
