"""Connectome vs an ensemble of nulls, with null variance separated from seed variance.

The original harness drew exactly one null graph per condition per seed, from the same RNG
as the task, so "null variance" and "seed variance" were the same number and neither could
be estimated. Here the null ensemble has its own RNG stream: draw d of a null type is the
same graph for every task seed, so the two sources of variance are separable.

Arms are compared at matched non-input firing rate, not matched syn_scale and not matched
spectral radius. The gain sweep showed that equal spectral radius still leaves ~50x activity
differences between arms, so matching rho alone does not isolate structure from excitability.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import e1_reservoir as H
from flylab.dynamics import LIFParams, post_pre_from_pre_post
from flylab.graph import load_graph, induced_subgraph
from flylab.nulls import degree_preserving_null, er_graph
from flylab.spectral import arm_spectrum, gain_for_target_rate, syn_scale_for_gain

NULL_STREAM = 90_000  # RNG stream for null draws; deliberately disjoint from task seeds


def make_trials_for(cfg, n, seed):
    rng = np.random.default_rng(seed)
    I_list, y, inputs = H.make_trials(n, cfg, rng)
    tr, te = [], []
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        cut = int(0.7 * len(idx))
        tr.extend(idx[:cut].tolist())
        te.extend(idx[cut:].tolist())
    return I_list, y, inputs, np.array(tr), np.array(te)


def evaluate(W, rho, gain, I_list, y, tr, te, inputs, cfg, seed, n_probes):
    base = cfg["dynamics"]["lif"]
    ss = syn_scale_for_gain(rho, gain, base["tau_m"], base.get("dt", 1.0))
    lif = LIFParams(**{**base, "syn_scale": ss})
    X, st = H.reservoir_features(W, I_list, lif, seed, input_ids=inputs, n_probes=n_probes)
    liveness = H.check_alive(X, st, "null_ensemble", cfg.get("harness_guards", {}))
    if not liveness["alive"]:
        return {
            "acc": None, "non_input_spikes": st["pool_spikes"], "syn_scale": ss,
            "gain": gain, "liveness": liveness, "scoring_skipped": True,
        }
    r = H.ridge_sweep(X[tr], y[tr], X[te], y[te], cfg["dynamics"]["n_classes"], seed=seed)
    return {
        "acc": r["acc"], "train_acc": r["train_acc"],
        "train_test_gap": r["train_test_gap"], "selected_ridge": r["selected_ridge"],
        "non_input_spikes": st["pool_spikes"], "syn_scale": ss, "gain": gain,
        "ridge_curve": r["curve"], "liveness": liveness,
    }


def match_gain(W, rho, I_match, inputs, cfg, seed, n_pool, target_rate):
    base = cfg["dynamics"]["lif"]

    def rate_fn(gain):
        ss = syn_scale_for_gain(rho, gain, base["tau_m"], base.get("dt", 1.0))
        _, st = H.reservoir_features(W, I_match, LIFParams(**{**base, "syn_scale": ss}),
                                     seed, input_ids=inputs, n_probes=8)
        return st["pool_spikes"] / (len(I_match) * cfg["dynamics"]["n_steps"] * n_pool)

    return gain_for_target_rate(rate_fn, target_rate, lo=0.05, hi=80.0)


def ci95(v):
    v = np.asarray(v, dtype=float)
    return float(1.96 * v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else 0.0


def main(argv=None):
    ap = argparse.ArgumentParser(description="E1 connectome vs null ensemble")
    ap.add_argument("--seeds", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--draws", type=int, default=20, help="null graphs per null type")
    ap.add_argument("--n-trials", type=int, default=40)
    ap.add_argument("--n-probes", type=int, default=48)
    ap.add_argument("--target-rate", type=float, default=0.002)
    ap.add_argument("--swaps-per-edge", type=int, default=5)
    ap.add_argument("--prefix", default="e1_null_ensemble")
    args = ap.parse_args(argv)

    seeds = [int(s) for s in args.seeds.split(",")]
    cfg = H.load_cfg()
    cfg.setdefault("harness_guards", {})["on_dead"] = "record"
    if args.n_trials:
        cfg["dynamics"]["n_trials_per_class"] = args.n_trials
    t_start = time.time()

    print("loading graph...", flush=True)
    g = load_graph(load_neurons=False)
    nodes = H.select_nodes(g, cfg["subgraph"]["n"])
    A, nodes = induced_subgraph(g, nodes)
    W_conn = post_pre_from_pre_post(A)
    n, nnz = A.shape[0], int(W_conn.nnz)
    mask = np.isin(g.src, nodes) & np.isin(g.dst, nodes)
    remap = -np.ones(g.n, dtype=np.int64)
    remap[nodes] = np.arange(n)
    s, t = remap[g.src[mask]], remap[g.dst[mask]]
    sw = g.signed_weight[mask]

    print(f"building {args.draws} null draws per type (RNG stream {NULL_STREAM}, "
          "independent of task seeds)...", flush=True)
    graphs = {"connectome_signed": [W_conn]}
    null_diag = []
    dp, er = [], []
    for d in range(args.draws):
        rng_d = np.random.default_rng([NULL_STREAM, d])
        Wd, diag = degree_preserving_null(s, t, sw, n, rng_d, args.swaps_per_edge)
        dp.append(Wd)
        null_diag.append({"draw": d, **diag})
        er.append(er_graph(n, nnz, np.random.default_rng([NULL_STREAM + 1, d])))
    graphs["degree_preserving_null"] = dp
    graphs["er_null"] = er
    print(f"  nulls built in {time.time() - t_start:.1f}s", flush=True)

    spectra = {k: [arm_spectrum(W) for W in v] for k, v in graphs.items()}

    # One rate match per graph, on seed 0's drive. Gain is a property of the graph; the
    # drive statistics are identical across seeds by construction.
    I0, y0, in0, tr0, te0 = make_trials_for(cfg, n, seeds[0])
    n_pool = n - len(in0)
    stride = max(1, len(I0) // 20)
    I_match = I0[::stride]
    gains = {}
    for name, Ws in graphs.items():
        gains[name] = []
        for i, W in enumerate(Ws):
            m = match_gain(W, spectra[name][i]["rho_signed"], I_match, in0, cfg, seeds[0],
                           n_pool, args.target_rate)
            gains[name].append(m)
        print(f"  {name}: matched gains "
              f"{np.round([m['gain'] for m in gains[name]], 2).tolist()[:5]}... "
              f"converged={sum(m['converged'] for m in gains[name])}/{len(gains[name])}",
              flush=True)
    print(f"  rate matching done at {time.time() - t_start:.1f}s", flush=True)

    rows = []
    mlp_rows = []
    for seed in seeds:
        I_list, y, inputs, tr, te = make_trials_for(cfg, n, seed)
        for name, Ws in graphs.items():
            for i, W in enumerate(Ws):
                r = evaluate(W, spectra[name][i]["rho_signed"], gains[name][i]["gain"],
                             I_list, y, tr, te, inputs, cfg, seed, args.n_probes)
                rows.append({"seed": seed, "arm": name, "draw": i, **r})
        # parameter-matched MLP on the connectome features, same operating point
        base = cfg["dynamics"]["lif"]
        ss = syn_scale_for_gain(spectra["connectome_signed"][0]["rho_signed"],
                                gains["connectome_signed"][0]["gain"], base["tau_m"])
        X, mlp_stats = H.reservoir_features(
            W_conn, I_list, LIFParams(**{**base, "syn_scale": ss}), seed,
            input_ids=inputs, n_probes=args.n_probes,
        )
        budget = H.readout_params(X.shape[1], cfg["dynamics"]["n_classes"])
        mlp_live = H.check_alive(X, mlp_stats, "null_ensemble_mlp", cfg["harness_guards"])
        if mlp_live["alive"]:
            acc, params, info = H.mlp_baseline(X[tr], y[tr], X[te], y[te],
                                               cfg["dynamics"]["n_classes"],
                                               np.random.default_rng(seed), param_budget=budget)
            mlp_rows.append({"seed": seed, "acc": acc, "params": params,
                             "param_budget": budget, "liveness": mlp_live, **info})
        else:
            mlp_rows.append({"seed": seed, "acc": None, "param_budget": budget,
                             "liveness": mlp_live, "scoring_skipped": True})
        print(f"  seed {seed} done at {time.time() - t_start:.1f}s", flush=True)

    expected_rows = len(seeds) * (1 + 2 * args.draws)
    validity_failures = [
        {"seed": r["seed"], "arm": r["arm"], "draw": r["draw"],
         "reason": r.get("liveness", {}).get("dead_reason", "missing/invalid measurement")}
        for r in rows if not r.get("liveness", {}).get("alive", False)
    ]
    validity_failures.extend(
        {"seed": r["seed"], "arm": "mlp", "reason": r.get("liveness", {}).get("dead_reason", "invalid")}
        for r in mlp_rows if not r.get("liveness", {}).get("alive", False)
    )
    task_valid = (len(rows) == expected_rows and len(mlp_rows) == len(seeds)
                  and not validity_failures)
    comparisons = {}
    if task_valid:
        conn = np.array([r["acc"] for r in rows if r["arm"] == "connectome_signed"])
        agg = {"connectome_signed": {"mean_acc": float(conn.mean()), "ci95": ci95(conn),
                                     "per_seed": conn.tolist(), "n_seeds": len(conn)}}
        for name in ("degree_preserving_null", "er_null"):
            M = np.array([[next(r["acc"] for r in rows
                                if r["arm"] == name and r["seed"] == sd and r["draw"] == d)
                           for d in range(args.draws)] for sd in seeds])
            per_draw, per_seed = M.mean(axis=0), M.mean(axis=1)
            agg[name] = {"mean_acc": float(M.mean()), "ci95_over_draws": ci95(per_draw),
                         "sd_between_draws": float(per_draw.std(ddof=1)),
                         "sd_between_seeds": float(per_seed.std(ddof=1)),
                         "n_draws": args.draws, "n_seeds": len(seeds)}
            diff = conn - per_seed
            comparisons[f"connectome_vs_{name}"] = {
                "mean_diff": float(diff.mean()), "ci95_diff": ci95(diff),
                "per_seed_diff": diff.tolist(),
                "ci_excludes_zero": bool(abs(diff.mean()) > ci95(diff)) if len(diff) > 1 else False,
                "connectome_percentile_in_null_draws": float((per_draw < conn.mean()).mean()),
                "empirical_p_one_sided": float((per_draw >= conn.mean()).mean()),
            }
        mlp_acc = np.array([m["acc"] for m in mlp_rows])
        agg["mlp"] = {"mean_acc": float(mlp_acc.mean()), "ci95": ci95(mlp_acc),
                      "params": mlp_rows[0]["params"], "param_budget": mlp_rows[0]["param_budget"],
                      "width": mlp_rows[0]["width"], "within_budget": mlp_rows[0]["within_budget"]}
    else:
        agg = {name: {"mean_acc": None, "ci95": None, "claim_metric_withheld": True}
               for name in ("connectome_signed", "degree_preserving_null", "er_null", "mlp")}
        agg["valid_measurement_count"] = sum(
            r.get("liveness", {}).get("alive", False) for r in rows
        )

    summary = {
        "provenance": H.provenance(),
        "config": cfg,
        "settings": vars(args),
        "n": n, "nnz": nnz,
        "null_rng_stream": NULL_STREAM,
        "null_diagnostics": null_diag,
        "spectra": {k: v[0] for k, v in spectra.items()},
        "matched_gains": {k: [m["gain"] for m in v] for k, v in gains.items()},
        "gain_match_converged": {k: int(sum(m["converged"] for m in v)) for k, v in gains.items()},
        "rows": rows, "mlp": mlp_rows,
        "aggregate": agg,
        "comparisons": comparisons,
        "task_validity": {"valid_for_claims": task_valid, "expected_measurements": expected_rows,
                          "recorded_measurements": len(rows), "failures": validity_failures},
        "seconds": time.time() - t_start,
    }
    out = H.write_result(summary, prefix=args.prefix)
    print("\naggregate:", json.dumps(
        {k: {kk: vv for kk, vv in v.items() if kk != "per_seed"} for k, v in agg.items()},
        indent=2), flush=True)
    print("comparisons:", json.dumps(
        {k: {kk: vv for kk, vv in v.items() if kk != "per_seed_diff"}
         for k, v in comparisons.items()}, indent=2), flush=True)
    print(f"total {summary['seconds']:.1f}s", flush=True)
    print("WROTE", out, flush=True)


if __name__ == "__main__":
    main()
