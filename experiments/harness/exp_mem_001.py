"""Small exploratory pilot for EXP-MEM-001; it is not claim-ready evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
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
from flylab.dynamics import LIFParams, post_pre_from_pre_post
from flylab.graph import induced_subgraph, load_graph
from flylab.spectral import spectral_radius, syn_scale_for_gain
from memory_task import (combine_split_liveness, delay_line_recall, make_binary_trials,
                         simulate_terminal_features)

# GUESS: exploratory defaults only; revise using pilot timing and validity before preregistration.
PILOT_NODES = 128  # GUESS: small CPU pilot size; not a confirmatory subgraph size.
PILOT_LAGS = "1,4,16"  # GUESS: spread-out smoke lags; pilot-only, not the frozen lag grid.
PILOT_TRIALS_PER_CLASS = 20  # GUESS: enough for a pipeline smoke, not adequate power.
PILOT_SEED = 0  # GUESS: reproducibility seed for one exploratory pass, not inference.
PILOT_PROBES = 48  # GUESS: initial readout width; re-evaluate for memory before freeze.
PILOT_GAIN = 12.0  # GUESS: ignition-scale starting point only; measure, do not transfer as a MEM setting.
MEMORY_CLASSES = 2  # SOURCE: the preregistered cue variable is binary.


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_new_result(payload: dict) -> Path:
    out_dir = ROOT / "experiments/results/EXP-MEM-001"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rev = H.provenance().get("git_rev", "unknown")
    path = out_dir / f"pilot_{stamp}_{rev}.json"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite result: {path}")
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    tmp.replace(path)
    return path


def run_pilot(args) -> dict:
    cfg = H.load_cfg()
    guards = dict(cfg.get("harness_guards", {}))
    guards.update({"on_dead": "record", "min_unique_feature_rows": 2})
    graph = load_graph(load_neurons=False)
    nodes = H.select_nodes(graph, args.n)
    A, nodes = induced_subgraph(graph, nodes)
    W = post_pre_from_pre_post(A)
    n = W.shape[0]

    rng_inputs = np.random.default_rng(args.seed)
    n_inputs = max(1, int(round(n * cfg["dynamics"]["input_fraction"])))
    inputs = np.sort(rng_inputs.choice(n, size=n_inputs, replace=False))
    probes, _ = H.probe_set(n, input_ids=inputs, n_probes=min(args.n_probes, n - n_inputs))

    base = dict(cfg["dynamics"]["lif"])
    rho = spectral_radius(W)
    lif = LIFParams(**{
        **base,
        "syn_scale": syn_scale_for_gain(
            rho, args.gain, base["tau_m"], base.get("dt", 1.0), base.get("r", 1.0)
        ),
    })
    # SOURCE: one-step input current that reaches v_th from v_rest under the LIF update.
    cue_amplitude = (lif.v_th - lif.v_rest) * lif.tau_m / (lif.r * lif.dt)
    rows = []
    for lag in args.lags:
        start_wall, start_cpu = time.perf_counter(), time.process_time()
        train_drive, y_train = make_binary_trials(
            n, inputs, args.trials_per_class, lag, cue_amplitude,
            np.random.SeedSequence([args.seed, lag, 0]).generate_state(1)[0],
        )
        test_drive, y_test = make_binary_trials(
            n, inputs, args.trials_per_class, lag, cue_amplitude,
            np.random.SeedSequence([args.seed, lag, 1]).generate_state(1)[0],
        )
        X_train, st_train = simulate_terminal_features(W, train_drive, lif, inputs, probes, args.seed)
        X_test, st_test = simulate_terminal_features(W, test_drive, lif, inputs, probes, args.seed + 1)
        X_all = np.concatenate([X_train, X_test])
        stats = {
            "pool_spikes": st_train["pool_spikes"] + st_test["pool_spikes"],
            "probe_spikes": st_train["probe_spikes"] + st_test["probe_spikes"],
        }
        summary_live = H.check_alive(X_all, stats, f"mem_connectome_lag_{lag}", guards)
        train_live = H.check_alive(X_train, st_train, f"mem_connectome_lag_{lag}_train", guards)
        test_live = H.check_alive(X_test, st_test, f"mem_connectome_lag_{lag}_test", guards)
        live = combine_split_liveness(summary_live, train_live, test_live)
        score = None
        if live["alive"]:
            score = H.ridge_sweep(
                X_train, y_train, X_test, y_test, MEMORY_CLASSES, seed=args.seed
            )
        # SOURCE: the FIFO capacity is set to the largest lag under test in this pilot.
        capacity = max(args.lags)
        line_predictions = np.array(
            [delay_line_recall(int(y), lag, capacity) for y in y_test], dtype=np.int64
        )
        memoryless_predictions = np.zeros_like(y_test)
        n_pool = n - len(inputs)
        steps = lag + 1
        total_steps = (len(y_train) + len(y_test)) * steps * n_pool
        rows.append({
            "lag_steps": lag,
            "train_trials": int(len(y_train)),
            "test_trials": int(len(y_test)),
            "readout_window_steps": 1,
            "probe_ids_exclude_inputs": bool(not np.intersect1d(inputs, probes).size),
            "external_input_after_onset_nonzero_count": int(np.count_nonzero(test_drive[:, 1:, :])),
            "liveness": live,
            "scoring_skipped": not live["alive"],
            "accuracy": score["acc"] if score else None,
            "selected_ridge": score["selected_ridge"] if score else None,
            "delay_line_positive_control_accuracy": float((line_predictions == y_test).mean()),
            "memoryless_control_accuracy": float((memoryless_predictions == y_test).mean()),
            "realised_non_input_rate": float(stats["pool_spikes"] / total_steps),
            "wall_seconds": time.perf_counter() - start_wall,
            "cpu_seconds": time.process_time() - start_cpu,
        })

    return {
        "experiment_id": "EXP-MEM-001",
        "stage": "exploratory_pilot_only",
        "claim_ready": False,
        "protocol_frozen": False,
        "provenance": H.provenance(),
        "graph_sha256": {
            name: sha256_file(ROOT / "data/derived/graph" / name)
            for name in ("csr_unsigned.npz", "csc_unsigned.npz", "coo_signed.npz")
        },
        "task": "binary cue at t=0, silent delay, classify from final-step non-input spikes",
        "control_note": "The delay line validates task/evaluator plumbing; it is not a neural architecture result.",
        "operating_point_note": "Gain is exploratory; this pilot does not claim matched-rate comparisons.",
        "settings": vars(args),
        "n_nodes": int(n),
        "n_inputs": int(len(inputs)),
        "n_probes": int(len(probes)),
        "rho_signed": float(rho),
        "syn_scale": float(lif.syn_scale),
        "cue_amplitude": float(cue_amplitude),
        "rows": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", action="store_true", help="run only a low-cost exploratory pilot")
    parser.add_argument("--n", type=int, default=PILOT_NODES)
    parser.add_argument("--lags", type=lambda s: [int(x) for x in s.split(",")],
                        default=[int(x) for x in PILOT_LAGS.split(",")])
    parser.add_argument("--trials-per-class", type=int, default=PILOT_TRIALS_PER_CLASS)
    parser.add_argument("--seed", type=int, default=PILOT_SEED)
    parser.add_argument("--n-probes", type=int, default=PILOT_PROBES)
    parser.add_argument("--gain", type=float, default=PILOT_GAIN)
    args = parser.parse_args(argv)
    if not args.pilot:
        parser.error("only --pilot is implemented; freeze a preregistered protocol before confirmation")
    if not args.lags or any(lag < 0 for lag in args.lags) or len(set(args.lags)) != len(args.lags):
        parser.error("lags must be distinct nonnegative integers")
    result = run_pilot(args)
    path = write_new_result(result)
    print(json.dumps({
        "result": str(path),
        "claim_ready": result["claim_ready"],
        "rows": [{k: r[k] for k in ("lag_steps", "accuracy", "liveness", "wall_seconds",
                                     "cpu_seconds", "realised_non_input_rate")}
                 for r in result["rows"]],
    }, indent=2))


if __name__ == "__main__":
    main()
