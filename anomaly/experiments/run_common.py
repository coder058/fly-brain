from __future__ import annotations
import json, time, sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from anomaly.signals import make_dataset
from anomaly.baselines import (
    score_threshold, score_pca, score_isolation_forest, score_ocsvm, score_mlp_recon,
)
from anomaly.metrics import summarize
from anomaly import fly_scorer as FS
from flylab.graph import load_graph
from flylab.dynamics import LIFParams
from flylab.spectral import arm_spectrum, syn_scale_for_gain

OUT = ROOT / "anomaly" / "results"
OUT.mkdir(parents=True, exist_ok=True)


def split_xy(X, y, seed=0, train_frac=0.7, temporal=False):
    """Train on normals only. If temporal, keep generation order (no shuffle)."""
    rng = np.random.default_rng(seed)
    normal_idx = np.where(y == 0)[0]
    anom_idx = np.where(y == 1)[0]
    if not temporal:
        rng.shuffle(normal_idx)
    cut = int(train_frac * len(normal_idx))
    tr_n, te_n = normal_idx[:cut], normal_idx[cut:]
    te = np.concatenate([te_n, anom_idx])
    if not temporal:
        rng.shuffle(te)
    return X[tr_n], y[tr_n], X[te], y[te]


def run_exp(exp_id: str, *, n_normal, n_anom, T, seed, anom_kind, noise, anom_strength, n_nodes=128, temporal_split=False, shuffle=True):
    t0 = time.time()
    X, y = make_dataset(
        n_normal=n_normal, n_anom=n_anom, T=T, n_channels=8, seed=seed,
        anom_kind=anom_kind, noise=noise, anom_strength=anom_strength,
        shuffle=shuffle,
    )
    Xtr, ytr, Xte, yte = split_xy(X, y, seed=seed, temporal=temporal_split)
    results = {
        "exp": exp_id,
        "seed": seed,
        "utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "n_normal": n_normal, "n_anom": n_anom, "T": T,
            "anom_kind": anom_kind, "noise": noise, "anom_strength": anom_strength,
            "n_nodes": n_nodes, "prevalence": float(n_anom / (n_normal + n_anom)),
            "temporal_split": temporal_split,
        },
        "arms": {},
        "claim_ready": False,
        "note": "Ceiling AUROC≈1.0 on all arms means task too easy — not a topology claim.",
    }
    for name, fn in [
        ("threshold", lambda: score_threshold(Xtr, Xte)),
        ("pca", lambda: score_pca(Xtr, Xte)),
        ("isolation_forest", lambda: score_isolation_forest(Xtr, Xte, seed=seed)),
        ("ocsvm", lambda: score_ocsvm(Xtr, Xte)),
        ("mlp_recon", lambda: score_mlp_recon(Xtr, Xte, seed=seed)),
    ]:
        results["arms"][name] = summarize(yte, fn())

    g = load_graph()
    nodes = FS.select_top_nodes(g, n_nodes)
    input_ids = np.arange(12, dtype=np.int64)
    for mode in ("signed", "er_null", "abs"):
        W = FS.make_W_post_pre(g, nodes, mode=mode)
        try:
            spec = arm_spectrum(W.T.tocsr())
            rho = float(spec["rho_signed"] if mode != "abs" else spec["rho_abs"])
        except Exception:
            rho = 50.0
        ss = float(syn_scale_for_gain(max(rho, 1e-3), gain=5.0, tau_m=8.0, dt=1.0))
        lif = LIFParams(dt=1.0, tau_m=8.0, v_th=1.0, syn_scale=ss)
        emb_tr = np.stack([
            FS.reservoir_embed(W, FS.encode_to_current(Xtr[i], W.shape[0], input_ids), lif)
            for i in range(len(Xtr))
        ])
        emb_te = np.stack([
            FS.reservoir_embed(W, FS.encode_to_current(Xte[i], W.shape[0], input_ids), lif)
            for i in range(len(Xte))
        ])
        pool = np.ones(W.shape[0], dtype=bool); pool[input_ids] = False
        mu = FS.fit_mu(emb_tr[:, pool])
        s = FS.anomaly_score(emb_te[:, pool], mu)
        results["arms"][f"fly_{mode}"] = {
            **summarize(yte, s),
            "n_neurons": int(W.shape[0]),
            "nnz": int(W.nnz),
            "syn_scale": ss,
            "non_input_mean_rate": float(emb_te[:, pool].mean()),
        }

    aurocs = [results["arms"][k]["auroc"] for k in results["arms"]]
    results["ceiling_like"] = bool(min(aurocs) > 0.98)
    results["seconds"] = round(time.time() - t0, 2)
    results["n_train_normal"] = int(len(Xtr))
    results["n_test"] = int(len(Xte))
    results["n_test_anom"] = int((yte == 1).sum())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    num = exp_id.split("-")[-1].lower()
    path = OUT / f"exp_anom_{num}_{stamp}.json"
    path.write_text(json.dumps(results, indent=2) + "\n")
    return results, path
