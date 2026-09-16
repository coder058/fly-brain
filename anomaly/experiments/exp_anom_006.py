#!/usr/bin/env python3
"""EXP-ANOM-006 — connectome vs nulls, multi-seed (powered enough for a small claim).

Uses the EXP-002-like subtle local_glitch task (not ceiling). Compares:
  fly_signed, fly_abs, er_null, weight_perm (topology fixed), hub_removed
against threshold/pca baselines. Reports mean AUROC ± 95% CI across seeds.
"""
from __future__ import annotations
import json, time, sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_common import split_xy, OUT
from anomaly.signals import make_dataset
from anomaly.baselines import score_threshold, score_pca
from anomaly.metrics import summarize
from anomaly import fly_scorer as FS
from flylab.graph import load_graph
from flylab.dynamics import LIFParams, post_pre_from_pre_post
from flylab.spectral import arm_spectrum, syn_scale_for_gain


def ci95(xs):
    a = np.asarray(xs, dtype=float)
    if len(a) < 2:
        return float(a.mean()), 0.0
    se = a.std(ddof=1) / np.sqrt(len(a))
    return float(a.mean()), float(1.96 * se)


def weight_perm(W_post_pre, rng):
    """Permute nonzero weights on fixed topology (post×pre CSR)."""
    W = W_post_pre.tocsr().copy()
    data = W.data.copy()
    rng.shuffle(data)
    W.data = data
    return W


def remove_topk_hubs(W_post_pre, k_frac=0.05):
    """Zero rows/cols of top out-degree hubs (approx via col sums of post×pre = incoming from pre)."""
    W = W_post_pre.tocsr().copy()
    # out-degree of pre ≈ column nnz of W (W[post, pre])
    outdeg = np.diff(W.tocsc().indptr)
    k = max(1, int(k_frac * W.shape[0]))
    hubs = np.argsort(outdeg)[-k:]
    # zero hub as pre (columns) and as post (rows)
    for h in hubs:
        W.data[W.indptr[h]:W.indptr[h+1]] = 0  # as post row
    W = W.tocsc()
    for h in hubs:
        W.data[W.indptr[h]:W.indptr[h+1]] = 0
    return W.tocsr()


def score_fly(W, Xtr, Xte, input_ids, lif):
    emb_tr = np.stack([
        FS.reservoir_embed(W, FS.encode_to_current(Xtr[i], W.shape[0], input_ids), lif)
        for i in range(len(Xtr))
    ])
    emb_te = np.stack([
        FS.reservoir_embed(W, FS.encode_to_current(Xte[i], W.shape[0], input_ids), lif)
        for i in range(len(Xte))
    ])
    pool = np.ones(W.shape[0], dtype=bool)
    pool[input_ids] = False
    mu = FS.fit_mu(emb_tr[:, pool])
    return FS.anomaly_score(emb_te[:, pool], mu), float(emb_te[:, pool].mean())


def main():
    t0 = time.time()
    seeds = list(range(12))
    n_nodes = 128
    cfg = dict(n_normal=200, n_anom=50, T=48, anom_kind="local_glitch", noise=0.25, anom_strength=0.35)
    g = load_graph()
    nodes = FS.select_top_nodes(g, n_nodes)
    input_ids = np.arange(12, dtype=np.int64)

    # Prebuild arms that don't depend on seed (graphs); ER/weight_perm redrawn per seed
    W_signed = FS.make_W_post_pre(g, nodes, mode="signed")
    W_abs = FS.make_W_post_pre(g, nodes, mode="abs")

    def lif_for(W, mode_hint="signed"):
        try:
            spec = arm_spectrum(W.T.tocsr())
            rho = float(spec["rho_signed"] if mode_hint != "abs" else spec["rho_abs"])
        except Exception:
            rho = 50.0
        ss = float(syn_scale_for_gain(max(rho, 1e-3), gain=5.0, tau_m=8.0, dt=1.0))
        return LIFParams(dt=1.0, tau_m=8.0, v_th=1.0, syn_scale=ss), ss

    arm_names = ["threshold", "pca", "fly_signed", "fly_abs", "er_null", "weight_perm", "hubs_removed"]
    per_seed = []

    for seed in seeds:
        print(f"seed {seed}...", flush=True)
        rng = np.random.default_rng(1000 + seed)
        X, y = make_dataset(seed=seed, **cfg)
        Xtr, _, Xte, yte = split_xy(X, y, seed=seed)
        row = {"seed": seed, "arms": {}}

        row["arms"]["threshold"] = summarize(yte, score_threshold(Xtr, Xte))
        row["arms"]["pca"] = summarize(yte, score_pca(Xtr, Xte))

        for name, W, hint in [
            ("fly_signed", W_signed, "signed"),
            ("fly_abs", W_abs, "abs"),
        ]:
            lif, ss = lif_for(W, hint)
            s, rate = score_fly(W, Xtr, Xte, input_ids, lif)
            row["arms"][name] = {**summarize(yte, s), "syn_scale": ss, "non_input_mean_rate": rate}

        W_er = FS.make_W_post_pre(g, nodes, mode="er_null")
        # re-seed ER inside make uses fixed rng(0) — rebuild locally for seed diversity
        A, _ = __import__("flylab.graph", fromlist=["induced_subgraph"]).induced_subgraph(g, nodes)
        nnz = A.nnz
        k = len(nodes)
        flat = rng.choice(k * (k - 1), size=min(nnz, k * (k - 1)), replace=False)
        src = flat // (k - 1)
        dst = flat % (k - 1)
        dst = dst + (dst >= src).astype(np.int64)
        w = rng.choice(np.array([-1.0, 1.0], dtype=np.float32), size=len(src)) * rng.uniform(1, 10, len(src)).astype(np.float32)
        W_er = post_pre_from_pre_post(sparse.csr_matrix((w, (src, dst)), shape=(k, k)))
        lif, ss = lif_for(W_er, "signed")
        s, rate = score_fly(W_er, Xtr, Xte, input_ids, lif)
        row["arms"]["er_null"] = {**summarize(yte, s), "syn_scale": ss, "non_input_mean_rate": rate}

        W_wp = weight_perm(W_signed, rng)
        lif, ss = lif_for(W_wp, "signed")
        s, rate = score_fly(W_wp, Xtr, Xte, input_ids, lif)
        row["arms"]["weight_perm"] = {**summarize(yte, s), "syn_scale": ss, "non_input_mean_rate": rate}

        W_hub = remove_topk_hubs(W_signed, 0.05)
        lif, ss = lif_for(W_hub, "signed")
        s, rate = score_fly(W_hub, Xtr, Xte, input_ids, lif)
        row["arms"]["hubs_removed"] = {**summarize(yte, s), "syn_scale": ss, "non_input_mean_rate": rate}

        per_seed.append(row)

    agg = {}
    for name in arm_names:
        vals = [r["arms"][name]["auroc"] for r in per_seed]
        mean, half = ci95(vals)
        agg[name] = {"mean_auroc": mean, "ci95": half, "n": len(vals), "values": vals}

    conn = agg["fly_signed"]["mean_auroc"]
    er = agg["er_null"]["mean_auroc"]
    wp = agg["weight_perm"]["mean_auroc"]
    thr = agg["threshold"]["mean_auroc"]
    verdict = {
        "beats_er_null": bool(conn > er),
        "beats_weight_perm": bool(conn > wp),
        "beats_threshold_baseline": bool(conn > thr),
        "diff_vs_er": conn - er,
        "diff_vs_weight_perm": conn - wp,
        "diff_vs_threshold": conn - thr,
        "ANOMALY_TOPOLOGY_ADVANTAGE": False,  # set below
    }
    # Advantage only if beats both structural nulls by margin exceeding CI overlap crudely
    margin_er = (conn - er) - (agg["fly_signed"]["ci95"] + agg["er_null"]["ci95"])
    margin_wp = (conn - wp) - (agg["fly_signed"]["ci95"] + agg["weight_perm"]["ci95"])
    verdict["ANOMALY_TOPOLOGY_ADVANTAGE"] = bool(margin_er > 0 and margin_wp > 0 and conn > thr)

    out = {
        "exp": "EXP-ANOM-006",
        "utc": datetime.now(timezone.utc).isoformat(),
        "config": {**cfg, "n_nodes": n_nodes, "seeds": seeds},
        "aggregate": agg,
        "verdict": verdict,
        "seconds": round(time.time() - t0, 2),
        "note": "Subtle task; 12 seeds. Topology advantage requires beating ER + weight_perm with CI-separated margin and baseline.",
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT / f"exp_anom_006_{stamp}.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"aggregate": {k: {"mean": v["mean_auroc"], "ci95": v["ci95"]} for k,v in agg.items()}, "verdict": verdict}, indent=2))
    print("seconds", out["seconds"], "WROTE", path)


if __name__ == "__main__":
    main()
