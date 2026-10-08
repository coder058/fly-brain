"""E1-OP: does the E1 negative survive fixing two operating-point artifacts?

Diagnosis of the powered E1 run (e1_null_ensemble_powered_20260915T130422Z_fe089d3) found
two measurement artifacts that both penalise heterogeneous graphs more than random ones:

1. Global rate matching. `null_ensemble.py` matches each graph's gain once, on task seed
   0's drive, on the stated assumption that drive statistics are identical across seeds.
   They are not: `make_trials` draws a new set of 50 input neurons per seed. At the
   matched gain the connectome's non-input rate ranges from 0.01x to 1.97x of target
   across seeds 0-11 (seed 9 is effectively silent). Random nulls barely care which
   neurons are driven; a hub-structured connectome does.
2. Sparse probe readout. Features are read from 48 fixed random non-input neurons. The
   connectome's activity concentrates on few neurons, so on seed 5 the network fired
   20,231 non-input spikes but only 18 landed on the probes, and the readout scored at
   chance on its own training set. The liveness guard counts pool spikes, not probe
   spikes, so it passed.

This runner measures the full 2x2: gain matching {global, per_seed} x readout
{probe48, all non-input neurons}, for the connectome, 20 degree-preserving null draws
and 20 Erdos-Renyi draws, plus an input-only baseline that never touches a reservoir.
The global/probe48 cell reproduces the original measurement exactly (tested).
Protocol: experiments/results/EXP-E1-OP/protocol.md (committed before any run).
"""
from __future__ import annotations

import os

# One BLAS thread per worker: with the default thread pool, 4 workers oversubscribe the CPU and
# a 193-feature ridge sweep took 11 s instead of 0.02 s.
for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import e1_reservoir as H
from null_ensemble import NULL_STREAM, make_trials_for
from flylab.dynamics import LIFParams, LIFState, step_lif
from flylab.graph import GRAPH_DIR, load_graph
from flylab.nulls import degree_preserving_null, er_graph
from flylab.slice import Slice, from_full_graph, load_slice
from flylab.spectral import gain_for_target_rate, spectral_radius, syn_scale_for_gain

RESULTS = HERE.parents[1] / "experiments" / "results" / "EXP-E1-OP"
N_BINS = 4
MATCH_SEED = 0  # the original harness matched every graph on task seed 0's drive
READOUTS = ("probe48", "full")
MATCHINGS = ("global", "per_seed")


def build_arms(sl: Slice, draws: int, swaps_per_edge: int) -> dict:
    """Connectome + null draws on the E1 slice, with null_ensemble.py's RNG streams."""
    W_conn = sl.W()
    n, nnz = sl.n, int(W_conn.nnz)
    graphs = {"connectome_signed": [W_conn], "degree_preserving_null": [], "er_null": []}
    for d in range(draws):
        Wd, _ = degree_preserving_null(sl.src, sl.dst, sl.signed_weight, n,
                                       np.random.default_rng([NULL_STREAM, d]), swaps_per_edge)
        graphs["degree_preserving_null"].append(Wd)
        graphs["er_null"].append(er_graph(n, nnz, np.random.default_rng([NULL_STREAM + 1, d])))
    return graphs


def simulate_features(W, I_list, lif: LIFParams, seed: int, input_ids, n_probes: int = 48):
    """One LIF run per trial, two readouts from the same raster.

    `probe48` is bit-identical to `e1_reservoir.simulate_driven` (same initial state, same
    probe set); `full` bins every non-input neuron instead of 48 of them.
    """
    n = W.shape[0]
    probes, pool = H.probe_set(n, input_ids, n_probes)
    edges = None
    X_probe, X_full = [], []
    pool_spikes = probe_spikes = 0.0
    for i, I_seq in enumerate(I_list):
        T = I_seq.shape[0]
        rng = np.random.default_rng(seed + i)
        state = LIFState(v=rng.normal(lif.v_rest, 0.05, size=n).astype(np.float32),
                         spikes=np.zeros(n, dtype=np.float32))
        raster = np.zeros((T, n), dtype=np.float32)
        for t in range(T):
            state = step_lif(W, state, I_seq[t], lif)
            raster[t] = state.spikes
        if edges is None:
            edges = np.linspace(0, T, N_BINS + 1, dtype=int)
        bins = [raster[edges[b]:edges[b + 1]] for b in range(N_BINS)]
        X_probe.append(np.concatenate([b[:, probes].mean(axis=0) for b in bins]))
        X_full.append(np.concatenate([b[:, pool].mean(axis=0) for b in bins]))
        pool_spikes += float(raster[:, pool].sum())
        probe_spikes += float(raster[:, probes].sum())
    st = {"pool_spikes": pool_spikes, "probe_spikes": probe_spikes, "n_trials": len(I_list)}
    return {"probe48": np.stack(X_probe), "full": np.stack(X_full)}, st


def input_only_features(I_list, input_ids) -> np.ndarray:
    """No reservoir: mean drive over the input neurons in the same 4 time bins."""
    out = []
    for I_seq in I_list:
        T = I_seq.shape[0]
        edges = np.linspace(0, T, N_BINS + 1, dtype=int)
        trace = I_seq[:, input_ids].mean(axis=1)
        out.append([trace[edges[b]:edges[b + 1]].mean() for b in range(N_BINS)])
    return np.asarray(out, dtype=np.float64)


def lif_at(rho: float, gain: float, cfg: dict) -> LIFParams:
    base = cfg["dynamics"]["lif"]
    return LIFParams(**{**base, "syn_scale": syn_scale_for_gain(rho, gain, base["tau_m"],
                                                                base.get("dt", 1.0))})


def match_gain(W, rho, I_list, inputs, cfg, seed, target_rate, tol):
    n_pool = W.shape[0] - len(inputs)
    stride = max(1, len(I_list) // 20)
    I_match = I_list[::stride]
    T = cfg["dynamics"]["n_steps"]

    def rate_fn(gain):
        _, st = H.reservoir_features(W, I_match, lif_at(rho, gain, cfg), seed,
                                     input_ids=inputs, n_probes=8)
        return st["pool_spikes"] / (len(I_match) * T * n_pool)

    return gain_for_target_rate(rate_fn, target_rate, lo=0.05, hi=80.0, tol=tol)


# Worker state is set once in the parent and inherited by fork; graphs are small.
_STATE: dict = {}


def _score(X, y, tr, te, n_classes, seed):
    r = H.ridge_sweep(X[tr], y[tr], X[te], y[te], n_classes, seed=seed)
    return {"acc": r["acc"], "train_acc": r["train_acc"], "selected_ridge": r["selected_ridge"]}


def run_seed(seed: int) -> list[dict]:
    cfg, graphs, rhos, global_gain = (_STATE["cfg"], _STATE["graphs"], _STATE["rhos"],
                                      _STATE["global_gain"])
    target, tol, n_probes = _STATE["target_rate"], _STATE["tol"], _STATE["n_probes"]
    n_classes, T = cfg["dynamics"]["n_classes"], cfg["dynamics"]["n_steps"]
    I_list, y, inputs, tr, te = make_trials_for(cfg, next(iter(graphs.values()))[0].shape[0],
                                                seed)
    guards = cfg["harness_guards"]
    rows = []
    X_in = input_only_features(I_list, inputs)
    rows.append({"seed": seed, "arm": "input_only", "draw": 0, "matching": None,
                 "readout": "input4", **_score(X_in, y, tr, te, n_classes, seed)})
    for arm, Ws in graphs.items():
        for d, W in enumerate(Ws):
            rho = rhos[arm][d]
            per_seed = match_gain(W, rho, I_list, inputs, cfg, seed, target, tol)
            for matching, gain, converged in (
                ("global", global_gain[arm][d]["gain"], global_gain[arm][d]["converged"]),
                ("per_seed", per_seed["gain"], per_seed["converged"]),
            ):
                feats, st = simulate_features(W, I_list, lif_at(rho, gain, cfg), seed, inputs,
                                              n_probes)
                n_pool = W.shape[0] - len(inputs)
                rate = st["pool_spikes"] / (len(I_list) * T * n_pool)
                for readout in READOUTS:
                    X = feats[readout]
                    live = H.check_alive(X, st, f"{arm}/{matching}/{readout}", guards)
                    rate_ok = abs(rate - target) <= tol * target
                    row = {"seed": seed, "arm": arm, "draw": d, "matching": matching,
                           "readout": readout, "gain": float(gain),
                           "gain_converged": bool(converged), "rate": rate,
                           "rate_within_tol": bool(rate_ok),
                           "probe_spikes": st["probe_spikes"],
                           "pool_spikes": st["pool_spikes"], "alive": bool(live["alive"])}
                    if live["alive"]:
                        row.update(_score(X, y, tr, te, n_classes, seed))
                    else:
                        row.update({"acc": None, "dead_reason": live.get("dead_reason")})
                    rows.append(row)
    print(f"  seed {seed} done", flush=True)
    return rows


def paired_summary(rows: list[dict], seeds: list[int], matching: str, readout: str,
                   require_rate: bool) -> dict:
    """Connectome minus mean-over-valid-draws null, paired by seed, two-sided 95% t CI."""
    def valid(r):
        return (r["acc"] is not None and r["alive"]
                and (not require_rate or r["rate_within_tol"]))

    sel = [r for r in rows if r["matching"] == matching and r["readout"] == readout]
    out = {"matching": matching, "readout": readout, "rate_gate": require_rate, "arms": {},
           "comparisons": {}, "excluded_seeds": []}
    per_seed = {}
    for seed in seeds:
        c = [r for r in sel if r["seed"] == seed and r["arm"] == "connectome_signed"]
        entry = {"connectome_signed": c[0]["acc"] if c and valid(c[0]) else None}
        for null in ("degree_preserving_null", "er_null"):
            v = [r["acc"] for r in sel if r["seed"] == seed and r["arm"] == null and valid(r)]
            entry[null] = float(np.mean(v)) if v else None
            entry[f"{null}_valid_draws"] = len(v)
        per_seed[seed] = entry
        if entry["connectome_signed"] is None:
            out["excluded_seeds"].append({"seed": seed, "connectome_row": c[0] if c else None})
    for arm in ("connectome_signed", "degree_preserving_null", "er_null"):
        v = np.array([e[arm] for e in per_seed.values() if e[arm] is not None], dtype=float)
        out["arms"][arm] = {"mean_acc": float(v.mean()) if len(v) else None,
                            "n_seeds": int(len(v)), "per_seed": v.tolist()}
    for null in ("degree_preserving_null", "er_null"):
        diff = np.array([e["connectome_signed"] - e[null] for e in per_seed.values()
                         if e["connectome_signed"] is not None and e[null] is not None])
        if len(diff) > 1:
            half = float(stats.t.ppf(0.975, len(diff) - 1) * diff.std(ddof=1) / np.sqrt(len(diff)))
            out["comparisons"][f"connectome_vs_{null}"] = {
                "mean_diff": float(diff.mean()), "ci95_low": float(diff.mean() - half),
                "ci95_high": float(diff.mean() + half), "n": int(len(diff)),
                "ci_excludes_zero": bool(abs(diff.mean()) > half),
                "per_seed_diff": diff.tolist()}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", required=True, help="comma list or a:b range (b exclusive)")
    ap.add_argument("--draws", type=int, default=20)
    ap.add_argument("--n-trials", type=int, default=60)
    ap.add_argument("--n-probes", type=int, default=48)
    ap.add_argument("--target-rate", type=float, default=0.002)
    ap.add_argument("--tol", type=float, default=0.15)
    ap.add_argument("--swaps-per-edge", type=int, default=5)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--label", required=True, help="diagnostic | confirmatory")
    ap.add_argument("--graph", choices=("slice", "full"), default="slice",
                    help="bundled 500-neuron slice (default) or re-extract from the full graph")
    args = ap.parse_args(argv)
    if ":" in args.seeds:
        a, b = (int(x) for x in args.seeds.split(":"))
        seeds = list(range(a, b))
    else:
        seeds = [int(s) for s in args.seeds.split(",")]

    t0 = time.time()
    cfg = H.load_cfg()
    cfg.setdefault("harness_guards", {})["on_dead"] = "record"
    cfg["dynamics"]["n_trials_per_class"] = args.n_trials
    if args.graph == "full":
        sl, source = from_full_graph(load_graph(), cfg["subgraph"]["n"]), str(GRAPH_DIR)
    else:
        sl, source = load_slice(), "data/e1_slice/e1_slice_500.npz"
    graphs = build_arms(sl, args.draws, args.swaps_per_edge)
    rhos = {k: [spectral_radius(W) for W in v] for k, v in graphs.items()}
    n = graphs["connectome_signed"][0].shape[0]
    I0, _, in0, _, _ = make_trials_for(cfg, n, MATCH_SEED)
    global_gain = {k: [match_gain(W, rhos[k][i], I0, in0, cfg, MATCH_SEED, args.target_rate,
                                  args.tol) for i, W in enumerate(v)]
                   for k, v in graphs.items()}
    print(f"graphs + global gains ready at {time.time() - t0:.0f}s "
          f"(connectome gain {global_gain['connectome_signed'][0]['gain']:.3f})", flush=True)

    _STATE.update(cfg=cfg, graphs=graphs, rhos=rhos, global_gain=global_gain,
                  target_rate=args.target_rate, tol=args.tol, n_probes=args.n_probes)
    with mp.get_context("fork").Pool(args.workers) as pool:
        rows = [r for chunk in pool.map(run_seed, seeds, chunksize=1) for r in chunk]

    cells = [paired_summary(rows, seeds, m, r, require_rate=(m == "per_seed"))
             for m in MATCHINGS for r in READOUTS]
    inp = np.array([r["acc"] for r in rows if r["arm"] == "input_only"])
    summary = {
        "experiment": "EXP-E1-OP", "label": args.label, "provenance": H.provenance(),
        "settings": vars(args), "graph_source": source, "seeds": seeds, "n": n,
        "global_gains": {k: [m["gain"] for m in v] for k, v in global_gain.items()},
        "cells": cells,
        "input_only": {"mean_acc": float(inp.mean()), "per_seed": inp.tolist()},
        "rows": rows, "seconds": time.time() - t0,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = H.versioned_path(f"e1_op_{args.label}", results_dir=RESULTS)
    out.write_text(json.dumps(summary, indent=1, default=float) + "\n")
    for c in cells:
        print(f"[{c['matching']:>8} / {c['readout']:>7}] "
              + "  ".join(f"{k}={v['mean_acc']:.3f}(n={v['n_seeds']})" for k, v in c["arms"].items()
                          if v["mean_acc"] is not None))
        for k, v in c["comparisons"].items():
            print(f"     {k}: {v['mean_diff']:+.3f} [{v['ci95_low']:+.3f}, {v['ci95_high']:+.3f}] n={v['n']}")
    print(f"input_only={inp.mean():.3f}   total {summary['seconds']:.0f}s\nWROTE {out}", flush=True)


if __name__ == "__main__":
    main()
