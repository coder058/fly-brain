"""Glutamate polarity as an explicit sensitivity arm.

`connectome_signed` is built from per-presynaptic-neuron neurotransmitter predictions. Under
the mapping the harness shipped with, glutamate is neither excitatory nor inhibitory, so
glutamatergic edges carry weight zero: they are stored, counted in `ops_proxy`, and
contribute no current. This script measures what that choice costs and what changes if
glutamate is instead treated as inhibitory (GluCl-alpha) or excitatory.

Reads data/raw/ only to look up neurotransmitter names. Never writes there.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.feather as feather
from scipy import sparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import e1_reservoir as H
from flylab.dynamics import LIFParams, post_pre_from_pre_post
from flylab.graph import GRAPH_DIR, load_graph, load_meta
from flylab.polarity import POLICIES, load_policy, sign_series
from flylab.spectral import arm_spectrum, gain_for_target_rate, syn_scale_for_gain
from null_ensemble import ci95, make_trials_for, match_gain

RAW_NT = Path(__file__).resolve().parents[2] / (
    "data/raw/malecns_v1/body-neurotransmitters-male-cns-v1.0.feather"
)


def nt_by_body(column: str = "consensus_nt") -> dict:
    """Prefer ground_truth when present; else `column` (default consensus_nt)."""
    cols = ["body", "ground_truth", column]
    # de-dupe if column == ground_truth
    cols = list(dict.fromkeys(cols))
    t = feather.read_table(RAW_NT, columns=cols).to_pandas()
    out = {}
    for _, row in t.iterrows():
        gt = row.get("ground_truth")
        if gt is not None and str(gt).strip() and str(gt).lower() not in ("nan", "none"):
            out[int(row["body"])] = str(gt).strip().lower()
        else:
            v = row.get(column)
            out[int(row["body"])] = (
                "unclear" if v is None or str(v).lower() in ("nan", "none") else str(v).strip().lower()
            )
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="E1 glutamate polarity sensitivity arms")
    ap.add_argument("--seeds", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--policies", default="glutamate_unknown,glutamate_inhibitory,"
                                          "glutamate_excitatory")
    ap.add_argument("--n-trials", type=int, default=40)
    ap.add_argument("--n-probes", type=int, default=48)
    ap.add_argument("--target-rate", type=float, default=0.002)
    ap.add_argument("--prefix", default="e1_polarity_arms")
    args = ap.parse_args(argv)

    seeds = [int(s) for s in args.seeds.split(",")]
    policies = args.policies.split(",")
    cfg = H.load_cfg()
    cfg.setdefault("harness_guards", {})["on_dead"] = "record"
    cfg["dynamics"]["n_trials_per_class"] = args.n_trials
    t0 = time.time()

    print("loading graph + neuron ids...", flush=True)
    g = load_graph(load_neurons=True)
    nodes = H.select_nodes(g, cfg["subgraph"]["n"])
    n = len(nodes)
    mask = np.isin(g.src, nodes) & np.isin(g.dst, nodes)
    remap = -np.ones(g.n, dtype=np.int64)
    remap[nodes] = np.arange(n)
    s, t = remap[g.src[mask]], remap[g.dst[mask]]
    w_abs = np.abs(g.weight[mask]).astype(np.float32)
    pre_body = g.body_ids[g.src[mask]]

    print("reading neurotransmitter predictions from data/raw (read-only)...", flush=True)
    lut = nt_by_body(load_policy().get("nt_column", "consensus_nt"))
    nt = [lut.get(int(b), "unclear") for b in pre_body]
    nt_counts = {k: int(v) for k, v in
                 zip(*np.unique(np.array(nt, dtype=object).astype(str), return_counts=True))}

    arms = {}
    graphs = {}
    for pol in policies:
        sign = sign_series(nt, pol).to_numpy().astype(np.float32)
        sw = sign * w_abs
        A = sparse.csr_matrix((sw, (s, t)), shape=(n, n))
        W = post_pre_from_pre_post(A)
        graphs[pol] = W
        nz = int((sw != 0).sum())
        arms[pol] = {
            "policy": POLICIES[pol],
            "edges_total": int(len(sw)),
            "edges_excitatory": int((sign > 0).sum()),
            "edges_inhibitory": int((sign < 0).sum()),
            "edges_zeroed": int((sign == 0).sum()),
            "fraction_zeroed": float((sign == 0).mean()),
            "stored_nnz": int(W.nnz),
            "effective_nnz": nz,
            "ops_proxy_inflation": float(W.nnz / max(nz, 1)),
            "signed_weight_sum": float(sw.sum()),
            "excitatory_weight": float(sw[sw > 0].sum()),
            "inhibitory_weight": float(sw[sw < 0].sum()),
            "spectrum": arm_spectrum(W),
        }
        print(f"  {pol:<22} E={arms[pol]['edges_excitatory']:>6} "
              f"I={arms[pol]['edges_inhibitory']:>6} zero={arms[pol]['edges_zeroed']:>6} "
              f"({arms[pol]['fraction_zeroed']*100:.2f}%) rho={arms[pol]['spectrum']['rho_signed']:.1f} "
              f"ops_inflation={arms[pol]['ops_proxy_inflation']:.2f}x", flush=True)

    I0, y0, in0, tr0, te0 = make_trials_for(cfg, n, seeds[0])
    n_pool = n - len(in0)
    I_match = I0[:: max(1, len(I0) // 20)]
    for pol in policies:
        m = match_gain(graphs[pol], arms[pol]["spectrum"]["rho_signed"], I_match, in0, cfg,
                       seeds[0], n_pool, args.target_rate)
        arms[pol]["matched_gain"] = m
        print(f"  {pol:<22} matched gain={m['gain']:.2f} converged={m['converged']}",
              flush=True)

    base = cfg["dynamics"]["lif"]
    for seed in seeds:
        I_list, y, inputs, tr, te = make_trials_for(cfg, n, seed)
        for pol in policies:
            rho = arms[pol]["spectrum"]["rho_signed"]
            ss = syn_scale_for_gain(rho, arms[pol]["matched_gain"]["gain"], base["tau_m"])
            X, st = H.reservoir_features(graphs[pol], I_list,
                                         LIFParams(**{**base, "syn_scale": ss}), seed,
                                         input_ids=inputs, n_probes=args.n_probes)
            liveness = H.check_alive(X, st, f"polarity:{pol}", cfg["harness_guards"])
            if liveness["alive"]:
                r = H.ridge_sweep(X[tr], y[tr], X[te], y[te], cfg["dynamics"]["n_classes"],
                                  seed=seed)
                row = {"seed": seed, "acc": r["acc"], "train_test_gap": r["train_test_gap"],
                       "selected_ridge": r["selected_ridge"],
                       "non_input_spikes": st["pool_spikes"], "liveness": liveness}
            else:
                row = {"seed": seed, "acc": None, "non_input_spikes": st["pool_spikes"],
                       "liveness": liveness, "scoring_skipped": True}
            arms[pol].setdefault("per_seed", []).append(row)
    all_valid = all(
        len(arms[pol].get("per_seed", [])) == len(seeds)
        and all(row.get("liveness", {}).get("alive", False)
                for row in arms[pol].get("per_seed", []))
        for pol in policies
    )
    for pol in policies:
        valid_rows = [x for x in arms[pol]["per_seed"] if x.get("acc") is not None]
        arms[pol]["valid_seed_count"] = len(valid_rows)
        if all_valid:
            a = np.array([x["acc"] for x in valid_rows])
            arms[pol]["mean_acc"] = float(a.mean())
            arms[pol]["ci95"] = ci95(a)
        else:
            arms[pol]["mean_acc"] = None
            arms[pol]["ci95"] = None
            arms[pol]["claim_metric_withheld"] = True

    ref = policies[0]
    deltas = {}
    for pol in policies[1:]:
        if not all_valid:
            deltas[f"{pol}_minus_{ref}"] = {"mean_diff": None, "ci95_diff": None,
                                             "claim_metric_withheld": True}
            continue
        d = np.array([x["acc"] for x in arms[pol]["per_seed"]]) - np.array(
            [x["acc"] for x in arms[ref]["per_seed"]])
        deltas[f"{pol}_minus_{ref}"] = {
            "mean_diff": float(d.mean()), "ci95_diff": ci95(d),
            "ci_excludes_zero": bool(abs(d.mean()) > ci95(d)) if len(d) > 1 else False,
        }

    summary = {
        "provenance": H.provenance(),
        "config": cfg, "settings": vars(args), "seeds": seeds,
        "n": n, "nt_column": load_policy().get("nt_column", "consensus_nt"),
        "presynaptic_nt_counts_in_subgraph": nt_counts,
        "graph_meta": load_meta(GRAPH_DIR / "graph_meta.json"),
        "arms": arms, "deltas_vs_reference": deltas,
        "task_validity": {
            "valid_for_claims": all_valid,
            "planned_seed_count": len(seeds),
            "invalid_rows": [
                {"policy": pol, "seed": row["seed"],
                 "reason": row.get("liveness", {}).get("dead_reason", "missing/invalid")}
                for pol in policies for row in arms[pol].get("per_seed", [])
                if not row.get("liveness", {}).get("alive", False)
            ],
        },
        "seconds": time.time() - t0,
    }
    out = H.write_result(summary, prefix=args.prefix)
    print("\n" + json.dumps(
        {p: {k: arms[p][k] for k in ("fraction_zeroed", "ops_proxy_inflation", "mean_acc",
                                     "ci95", "signed_weight_sum")} for p in policies},
        indent=2), flush=True)
    print("deltas:", json.dumps(deltas, indent=2), flush=True)
    print("WROTE", out, flush=True)


if __name__ == "__main__":
    main()
