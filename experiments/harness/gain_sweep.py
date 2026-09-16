"""Sweep effective spectral gain and report activity + accuracy per arm.

Answers the question the harness never asked: at what operating point does this reservoir
actually compute? Every arm is normalised to the same effective gain, so gain is a
controlled variable rather than a by-product of each graph's weight scale.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import sparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import e1_reservoir as H
from flylab.dynamics import LIFParams, post_pre_from_pre_post
from flylab.graph import load_graph, induced_subgraph
from flylab.spectral import arm_spectrum, syn_scale_for_gain


def build_arms(g, nodes, cfg, rng):
    A, nodes = induced_subgraph(g, nodes)
    n = A.shape[0]
    W_conn = post_pre_from_pre_post(A)
    mask = np.isin(g.src, nodes) & np.isin(g.dst, nodes)
    remap = -np.ones(g.n, dtype=np.int64)
    remap[nodes] = np.arange(n)
    s, t = remap[g.src[mask]], remap[g.dst[mask]]
    W_abs = sparse.csr_matrix(
        (np.abs(g.weight[mask]).astype(np.float32), (t, s)), shape=(n, n)
    )
    W_er = H.make_er(n, int(W_conn.nnz), rng)
    W_shuf = H.degree_shuffle(
        s.astype(np.int32), t.astype(np.int32), g.signed_weight[mask], n, rng
    )
    return n, {
        "connectome_signed": W_conn,
        "connectome_abs": W_abs,
        "er_null": W_er,
        "degree_shuffle": W_shuf,
    }


def split(y):
    tr, te = [], []
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        cut = int(0.7 * len(idx))
        tr.extend(idx[:cut].tolist())
        te.extend(idx[cut:].tolist())
    return np.array(tr, dtype=np.int64), np.array(te, dtype=np.int64)


def sweep(cfg, gains, seeds, arms_filter=None, n_probes=48):
    print("loading graph...", flush=True)
    g = load_graph(load_neurons=False)
    nodes = H.select_nodes(g, cfg["subgraph"]["n"])
    n_classes = cfg["dynamics"]["n_classes"]
    base = cfg["dynamics"]["lif"]
    rows = []
    spectra = {}
    for seed in seeds:
        rng = np.random.default_rng(seed)
        n, Ws = build_arms(g, nodes, cfg, rng)
        if arms_filter:
            Ws = {k: v for k, v in Ws.items() if k in arms_filter}
        I_list, y, inputs = H.make_trials(n, cfg, rng)
        tr, te = split(y)
        n_pool = n - len(inputs)
        for name, W in Ws.items():
            spec = arm_spectrum(W)
            spectra.setdefault(name, spec)
            for gain in gains:
                ss = syn_scale_for_gain(spec["rho_signed"], gain, base["tau_m"],
                                        base.get("dt", 1.0), base.get("r", 1.0))
                lif = LIFParams(**{**base, "syn_scale": ss})
                X, st = H.reservoir_features(W, I_list, lif, seed, input_ids=inputs,
                                             n_probes=n_probes)
                acc = H.accuracy(
                    H.predict(H.fit_readout(X[tr], y[tr], n_classes), X[te]), y[te]
                )
                rows.append({
                    "seed": seed, "arm": name, "gain": gain, "syn_scale": ss,
                    "non_input_spikes": st["pool_spikes"],
                    "probe_spikes": st["probe_spikes"],
                    "non_input_rate": st["pool_spikes"]
                    / (len(I_list) * cfg["dynamics"]["n_steps"] * n_pool),
                    "alive": bool(st["pool_spikes"] > 0),
                    "acc": acc,
                })
                print(f"  seed={seed} {name:<18} gain={gain:<6.3f} syn_scale={ss:.6f} "
                      f"spikes={st['pool_spikes']:>8.0f} acc={acc:.4f}", flush=True)
    return rows, spectra


def aggregate(rows):
    out = {}
    for r in rows:
        k = (r["arm"], r["gain"])
        out.setdefault(k, {"acc": [], "spikes": [], "syn_scale": r["syn_scale"]})
        out[k]["acc"].append(r["acc"])
        out[k]["spikes"].append(r["non_input_spikes"])
    agg = []
    for (arm, gain), v in sorted(out.items()):
        a = np.array(v["acc"])
        agg.append({
            "arm": arm, "gain": gain, "syn_scale": v["syn_scale"],
            "mean_acc": float(a.mean()),
            "ci95": float(1.96 * a.std(ddof=1) / np.sqrt(len(a))) if len(a) > 1 else 0.0,
            "mean_non_input_spikes": float(np.mean(v["spikes"])),
            "n_seeds": len(a),
        })
    return agg


def main(argv=None):
    ap = argparse.ArgumentParser(description="E1 effective-gain sweep")
    ap.add_argument("--gains", default="",
                    help="comma-separated gains; default is 0.3-1.5 in 13 steps plus an "
                         "extension to 30 (the connectome does not ignite inside 0.3-1.5)")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--arms", default="")
    ap.add_argument("--n-probes", type=int, default=48)
    ap.add_argument("--prefix", default="e1_gain_sweep")
    args = ap.parse_args(argv)

    if args.gains:
        gains = [float(x) for x in args.gains.split(",")]
    else:
        gains = [round(x, 3) for x in np.linspace(0.3, 1.5, 13)] + [2.0, 3.0, 5.0, 8.0,
                                                                    12.0, 20.0, 30.0]
    seeds = [int(s) for s in args.seeds.split(",")]
    arms_filter = [a for a in args.arms.split(",") if a] or None

    cfg = H.load_cfg()
    rows, spectra = sweep(cfg, gains, seeds, arms_filter, args.n_probes)
    agg = aggregate(rows)
    summary = {
        "provenance": H.provenance(),
        "config": cfg,
        "gains": gains,
        "seeds": seeds,
        "n_probes": args.n_probes,
        "spectra": spectra,
        "rows": rows,
        "aggregate": agg,
    }
    ignition = {}
    for a in agg:
        if a["mean_non_input_spikes"] > 0 and a["arm"] not in ignition:
            ignition[a["arm"]] = {"first_live_gain": a["gain"], "syn_scale": a["syn_scale"]}
    decodable = {}
    chance = 1.0 / cfg["dynamics"]["n_classes"]
    for a in agg:
        if a["mean_acc"] > chance + 0.15 and a["arm"] not in decodable:
            decodable[a["arm"]] = {"first_gain": a["gain"], "syn_scale": a["syn_scale"],
                                   "mean_acc": a["mean_acc"]}
    summary["ignition"] = ignition
    summary["first_decodable"] = decodable
    out = H.write_result(summary, prefix=args.prefix)
    print("\nignition (first gain with any non-input spike):",
          json.dumps(ignition, indent=2), flush=True)
    print("first decodable (mean_acc > chance+0.15):", json.dumps(decodable, indent=2),
          flush=True)
    print("WROTE", out, flush=True)


if __name__ == "__main__":
    main()
