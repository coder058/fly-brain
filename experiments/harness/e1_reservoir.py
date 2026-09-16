"""E1: reservoir + linear readout vs nulls + MLP. Hardened synthetic task (no class-private channels)."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(ROOT))

from flylab.dynamics import LIFParams, LIFState, step_lif, post_pre_from_pre_post
from flylab.graph import load_graph, induced_subgraph
from flylab.nulls import degree_preserving_null
from flylab.spectral import arm_spectrum, effective_gain, syn_scale_for_gain

CFG_PATH = Path(__file__).with_name("e1_config.json")
RESULTS_DIR = ROOT / "experiments/results"


def load_cfg() -> dict:
    return json.loads(CFG_PATH.read_text())


def _git_rev() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def provenance() -> dict:
    """Identify the code and config that produced a result, without mutating either."""
    return {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_rev": _git_rev(),
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
        "config_sha256": hashlib.sha256(CFG_PATH.read_bytes()).hexdigest()[:16],
    }


def versioned_path(prefix: str, ext: str = ".json", results_dir: Path | None = None) -> Path:
    """Timestamped result path that never collides with an existing file."""
    d = results_dir or RESULTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p = d / f"{prefix}_{stamp}_{_git_rev()}{ext}"
    k = 1
    while p.exists():
        p = d / f"{prefix}_{stamp}_{_git_rev()}_{k}{ext}"
        k += 1
    return p


def write_result(summary: dict, prefix: str = "e1_pilot") -> Path:
    """Write a result to a fresh versioned file. Refuses to overwrite anything."""
    p = versioned_path(prefix)
    if p.exists():
        raise RuntimeError(f"refusing to overwrite existing result: {p}")
    p.write_text(json.dumps(summary, indent=2))
    return p


def select_nodes(g, n: int) -> np.ndarray:
    deg = np.diff(g.csr.indptr)
    return np.sort(np.argsort(deg)[-n:])


def make_er(n: int, nnz: int, rng: np.random.Generator) -> sparse.csr_matrix:
    max_e = n * (n - 1)
    nnz = min(nnz, max_e)
    flat = rng.choice(max_e, size=nnz, replace=False)
    src = flat // (n - 1)
    dst = flat % (n - 1)
    dst = dst + (dst >= src).astype(np.int64)
    w = rng.choice(np.array([-1.0, 1.0], dtype=np.float32), size=nnz) * rng.uniform(
        1.0, 10.0, size=nnz
    ).astype(np.float32)
    A = sparse.csr_matrix((w, (src, dst)), shape=(n, n))
    return post_pre_from_pre_post(A)


def degree_shuffle_v0_broken(src, dst, signed_w, n, rng: np.random.Generator) -> sparse.csr_matrix:
    """The original null, kept only so the audit's before/after is reproducible.

    Permuting `dst` and rebuilding a COO matrix lets scipy sum colliding duplicates: on the
    E1 subgraph this destroyed 1,881 of 23,708 edges (7.93%) and created 19 self-loops. The
    structural degree sequences are not preserved. Do not use as a null.
    """
    new_dst = dst.copy()
    rng.shuffle(new_dst)
    A = sparse.csr_matrix((signed_w.astype(np.float32), (src, new_dst)), shape=(n, n))
    return post_pre_from_pre_post(A)


def degree_shuffle(src, dst, signed_w, n, rng: np.random.Generator,
                   n_swaps_per_edge: int = 10, return_diag: bool = False):
    """Degree-preserving directed rewiring. Asserts both degree sequences are exact."""
    A, diag = degree_preserving_null(src, dst, signed_w, n, rng, n_swaps_per_edge)
    return (A, diag) if return_diag else A


def make_trials(n, cfg, rng):
    """Shared input set; class = distinct multi-pulse temporal code (same neurons)."""
    dyn = cfg["dynamics"]
    n_classes = dyn["n_classes"]
    n_trials = dyn["n_trials_per_class"]
    n_steps = dyn["n_steps"]
    n_in = max(8, int(n * dyn["input_fraction"]))
    inputs = rng.choice(n, size=n_in, replace=False)
    noise = float(dyn.get("input_noise", 0.35))
    amp = float(dyn["I_amp"])
    I_seq = []
    y = []
    # fixed orthogonal-ish templates: pulses at different offsets
    templates = []
    for c in range(n_classes):
        on = np.zeros(n_steps, dtype=np.float32)
        # two pulses: primary phase + secondary echo
        p1 = 4 + c * 8
        p2 = p1 + 12 + c
        w = 5
        on[p1 : p1 + w] = amp
        if p2 + w < n_steps:
            on[p2 : p2 + w] = amp * 0.7
        templates.append(on)
    for c in range(n_classes):
        for _ in range(n_trials):
            I = np.zeros((n_steps, n), dtype=np.float32)
            on = templates[c].copy()
            on = np.roll(on, int(rng.integers(-2, 3)))
            I[:, inputs] = on[:, None]
            I += rng.normal(0, noise, size=I.shape).astype(np.float32)
            I_seq.append(I)
            y.append(c)
    return I_seq, np.array(y, dtype=np.int64), inputs


PROBE_SEED = 0  # fixed across arms and seeds so every arm is read out from the same probes


def probe_set(n: int, input_ids=None, n_probes: int = 48, probe_seed: int = PROBE_SEED):
    """Probes drawn from non-input neurons only. Driven inputs carry the label verbatim."""
    pool = np.arange(n)
    if input_ids is not None and len(input_ids):
        pool = np.setdiff1d(pool, np.asarray(input_ids), assume_unique=False)
    return np.sort(np.random.default_rng(probe_seed).choice(
        pool, size=min(n_probes, len(pool)), replace=False)), pool


def simulate_driven(
    W,
    I_seq,
    p: LIFParams,
    seed: int,
    input_ids: np.ndarray | None = None,
    n_probes: int = 48,
    n_bins: int = 4,
    return_stats: bool = False,
):
    """I_seq: (T,N). Features from recurrence only — never readout the driven inputs."""
    n = W.shape[0]
    T = I_seq.shape[0]
    rng = np.random.default_rng(seed)
    state = LIFState(
        v=rng.normal(p.v_rest, 0.05, size=n).astype(np.float32),
        spikes=np.zeros(n, dtype=np.float32),
    )
    raster = np.zeros((T, n), dtype=np.float32)
    for t in range(T):
        state = step_lif(W, state, I_seq[t], p)
        raster[t] = state.spikes
    probes, pool = probe_set(n, input_ids, n_probes)
    edges = np.linspace(0, T, n_bins + 1, dtype=int)
    feats = [raster[edges[b] : edges[b + 1]][:, probes].mean(axis=0) for b in range(n_bins)]
    X = np.concatenate(feats)
    if not return_stats:
        return X
    driven = np.setdiff1d(np.arange(n), pool, assume_unique=False)
    return X, {
        "pool_spikes": float(raster[:, pool].sum()),
        "probe_spikes": float(raster[:, probes].sum()),
        "driven_spikes": float(raster[:, driven].sum()) if len(driven) else 0.0,
    }


def reservoir_features(W, I_list, lif: LIFParams, seed: int, input_ids=None, n_probes: int = 48):
    """Returns (X, stats). stats counts spikes outside the driven set — the liveness evidence."""
    out = [
        simulate_driven(W, I, lif, seed + i, input_ids=input_ids, n_probes=n_probes,
                        return_stats=True)
        for i, I in enumerate(I_list)
    ]
    X = np.stack([o[0] for o in out], axis=0)
    stats = {
        "pool_spikes": float(sum(o[1]["pool_spikes"] for o in out)),
        "probe_spikes": float(sum(o[1]["probe_spikes"] for o in out)),
        "driven_spikes": float(sum(o[1]["driven_spikes"] for o in out)),
        "n_trials": len(out),
    }
    return X, stats


RIDGE_GRID = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1e3, 1e4]


def fit_readout(X, y, n_classes, ridge=10.0):
    Y = np.eye(n_classes, dtype=np.float64)[y]
    Xb = np.concatenate([X, np.ones((X.shape[0], 1))], axis=1)
    A = Xb.T @ Xb + ridge * np.eye(Xb.shape[1])
    B = Xb.T @ Y
    return np.linalg.solve(A, B)


def readout_params(n_features: int, n_classes: int) -> int:
    return int(n_features * n_classes + n_classes)


def mlp_width_for_budget(d: int, n_classes: int, budget: int, tol: float = 0.10) -> tuple:
    """Widest hidden layer whose parameter count lands within `tol` of the readout budget.

    PROTOCOL.md:24 requires baselines within +/-10% of the readout's trainable parameter
    budget. The original width=32 MLP had 6,341 parameters against the readout's 965: 6.57x
    over, so it was not a matched baseline, it was a bigger model.
    """
    per_width = d + 1 + n_classes  # W1 + b1 + W2 columns
    width = max(1, int(round((budget - n_classes) / per_width)))
    best = min(
        (w for w in range(1, max(2, width + 3))),
        key=lambda w: abs(w * per_width + n_classes - budget),
    )
    params = best * per_width + n_classes
    return best, params, abs(params - budget) / budget <= tol


def ridge_sweep(Xtr, ytr, Xte, yte, n_classes, ridges=None, val_frac=0.3, seed=0):
    """Train/test accuracy across regularisation strength, with the operating point chosen
    on a validation split of TRAIN only.

    The harness hardcoded ridge=10.0. The literature effect this experiment is chasing shows
    up as a train/test gap that moves with regularisation strength, which a single ridge
    value cannot show.
    """
    ridges = list(ridges if ridges is not None else RIDGE_GRID)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(ytr))
    n_val = max(n_classes, int(round(val_frac * len(idx))))
    val_idx, sub_idx = idx[:n_val], idx[n_val:]
    curve = []
    for r in ridges:
        Wsub = fit_readout(Xtr[sub_idx], ytr[sub_idx], n_classes, ridge=r)
        val_acc = accuracy(predict(Wsub, Xtr[val_idx]), ytr[val_idx])
        Wfull = fit_readout(Xtr, ytr, n_classes, ridge=r)
        tr_acc = accuracy(predict(Wfull, Xtr), ytr)
        te_acc = accuracy(predict(Wfull, Xte), yte)
        curve.append({"ridge": r, "val_acc": val_acc, "train_acc": tr_acc,
                      "test_acc": te_acc, "train_test_gap": tr_acc - te_acc})
    best = max(curve, key=lambda c: (c["val_acc"], -c["ridge"]))
    return {
        "curve": curve,
        "selected_ridge": best["ridge"],
        "selected_by": "validation split of train (test never used for selection)",
        "acc": best["test_acc"],
        "train_acc": best["train_acc"],
        "train_test_gap": best["train_test_gap"],
    }


def predict(W, X):
    Xb = np.concatenate([X, np.ones((X.shape[0], 1))], axis=1)
    return (Xb @ W).argmax(axis=1)


def accuracy(yhat, y):
    return float((yhat == y).mean())


def mlp_baseline(Xtr, ytr, Xte, yte, n_classes, rng, width=None, steps=500, lr=0.05,
                 param_budget=None):
    d = Xtr.shape[1]
    within_budget = None
    if width is None:
        budget = param_budget or readout_params(d, n_classes)
        width, _, within_budget = mlp_width_for_budget(d, n_classes, budget)
    W1 = rng.normal(0, 0.05, size=(d, width))
    b1 = np.zeros(width)
    W2 = rng.normal(0, 0.05, size=(width, n_classes))
    b2 = np.zeros(n_classes)
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
    Xtr_n, Xte_n = (Xtr - mu) / sd, (Xte - mu) / sd
    for _ in range(steps):
        h = np.tanh(Xtr_n @ W1 + b1)
        logits = h @ W2 + b2
        e = np.exp(logits - logits.max(1, keepdims=True))
        p = e / e.sum(1, keepdims=True)
        Y = np.eye(n_classes)[ytr]
        dlogits = (p - Y) / len(ytr)
        dW2 = h.T @ dlogits
        db2 = dlogits.sum(0)
        dh = dlogits @ W2.T * (1 - h**2)
        dW1 = Xtr_n.T @ dh
        db1 = dh.sum(0)
        W2 -= lr * dW2
        b2 -= lr * db2
        W1 -= lr * dW1
        b1 -= lr * db1
    yhat = (np.tanh(Xte_n @ W1 + b1) @ W2 + b2).argmax(1)
    n_params = int(W1.size + b1.size + W2.size + b2.size)
    return accuracy(yhat, yte), n_params, {"width": int(width), "params": n_params,
                                           "within_budget": within_budget}


def ops_proxy(nnz, n_steps, n_trials):
    return float(2 * nnz * n_steps * n_trials)


def effective_nonzero_nnz(W):
    """Count executable synapses, excluding explicit zero entries in sparse W."""
    if sparse.issparse(W):
        return int(np.count_nonzero(W.data))
    return int(np.count_nonzero(W))


def lif_for_arm(W, cfg: dict, gain: float | None = None):
    """LIFParams for one arm, with syn_scale set by spectral normalisation when configured.

    Without this every arm ran at the same syn_scale, which means a different effective gain
    per arm (rho differs 49x between the connectome and its ER null). Comparing arms at
    uncontrolled operating points is not a comparison of network structure.
    """
    dyn = cfg["dynamics"]
    base = dict(dyn["lif"])
    mode = str(dyn.get("gain_normalization", "none")).lower()
    spec = arm_spectrum(W)
    if mode == "none":
        spec["mode"] = "none"
        spec["syn_scale"] = float(base["syn_scale"])
        spec["effective_gain"] = effective_gain(
            spec["rho_signed"], base["syn_scale"], base.get("tau_m", 20.0),
            base.get("dt", 1.0), base.get("r", 1.0),
        )
        return LIFParams(**base), spec
    rho = spec["rho_signed"] if mode == "spectral_signed" else spec["rho_abs"]
    g = float(dyn["gain"] if gain is None else gain)
    base["syn_scale"] = syn_scale_for_gain(
        rho, g, base.get("tau_m", 20.0), base.get("dt", 1.0), base.get("r", 1.0)
    )
    spec.update({"mode": mode, "gain": g, "rho_used": rho,
                 "syn_scale": base["syn_scale"], "effective_gain": g})
    return LIFParams(**base), spec


def check_alive(X: np.ndarray, stats: dict, arm: str, guards: dict) -> dict:
    """Liveness = the reservoir spiked outside the driven set.

    Feature variance is not evidence of that. With driven inputs left in the probe set the
    features vary wildly while every non-input neuron stays silent, which is exactly how the
    original variance-only guard was fooled into blessing a dead network.
    """
    std = float(X.std())
    nuniq = int(np.unique(np.round(X, 6), axis=0).shape[0])
    pool_spikes = float(stats["pool_spikes"])
    report = {
        "non_input_spikes": pool_spikes,
        "probe_spikes": float(stats["probe_spikes"]),
        "feature_std": std,
        "unique_feature_rows": nuniq,
        "non_input_active": bool(pool_spikes > 0.0),
        "alive": False,
    }
    if not guards.get("reject_dead_features", True):
        report["alive"] = report["non_input_active"]
        return report
    problems = []
    if pool_spikes < float(guards.get("min_non_input_spikes", 1)):
        problems.append(f"non_input_spikes={pool_spikes:.0f} (reservoir silent)")
    if std < float(guards.get("min_feature_std", 1e-6)):
        problems.append(f"feature_std={std:g}")
    if nuniq < int(guards.get("min_unique_feature_rows", 8)):
        problems.append(f"unique_feature_rows={nuniq}")
    if problems:
        msg = (
            f"dead reservoir for arm={arm}: " + ", ".join(problems) + ". "
            "Refusing to score — the readout would be decoding drive, not computation."
        )
        if str(guards.get("on_dead", "raise")).lower() == "raise":
            raise RuntimeError(msg)
        report["dead_reason"] = msg
        report["alive"] = False
        print("DEAD (recorded, not scored as evidence):", msg, flush=True)
    else:
        report["alive"] = True
    return report


def run_seed(g, nodes, cfg, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    A, nodes = induced_subgraph(g, nodes)
    n = A.shape[0]
    W_conn = post_pre_from_pre_post(A)
    nnz = int(W_conn.nnz)
    mask = np.isin(g.src, nodes) & np.isin(g.dst, nodes)
    remap = -np.ones(g.n, dtype=np.int64)
    remap[nodes] = np.arange(n)
    s, t = remap[g.src[mask]], remap[g.dst[mask]]
    W_abs = sparse.csr_matrix(
        (np.abs(g.weight[mask]).astype(np.float32), (t, s)), shape=(n, n)
    )
    W_er = make_er(n, nnz, rng)
    W_shuf = degree_shuffle(
        s.astype(np.int32), t.astype(np.int32), g.signed_weight[mask], n, rng
    )

    I_list, y, inputs = make_trials(n, cfg, rng)
    n_in = len(inputs)
    # temporal-block hold-out: within each class, last 30% of trials = test (no shuffle leak)
    tr, te = [], []
    for c in np.unique(y):
        idx_c = np.where(y == c)[0]
        cut = int(0.7 * len(idx_c))
        tr.extend(idx_c[:cut].tolist())
        te.extend(idx_c[cut:].tolist())
    tr, te = np.array(tr, dtype=np.int64), np.array(te, dtype=np.int64)
    n_steps = cfg["dynamics"]["n_steps"]
    n_classes = cfg["dynamics"]["n_classes"]

    guards = cfg.get("harness_guards", {})

    def _check_alive(X, stats, arm):
        return check_alive(X, stats, arm, guards)

    arms = {}
    named = [
        ("connectome_signed", W_conn),
        ("connectome_abs", W_abs),
        ("er_null", W_er),
        ("degree_shuffle", W_shuf),
    ]
    lifs = {name: lif_for_arm(W, cfg) for name, W in named}
    for name, W in named:
        t0 = time.time()
        lif, spec = lifs[name]
        X, stats = reservoir_features(W, I_list, lif, seed, input_ids=inputs)
        liveness = _check_alive(X, stats, name)
        if not liveness["alive"]:
            effective_nnz = effective_nonzero_nnz(W)
            arms[name] = {
                "acc": None,
                "seconds": time.time() - t0,
                "stored_nnz": int(W.nnz),
                "effective_nnz": effective_nnz,
                "ops_proxy": ops_proxy(effective_nnz, n_steps, len(I_list)),
                "readout_params": readout_params(X.shape[1], n_classes),
                "liveness": liveness,
                "spectrum": spec,
                "scoring_skipped": True,
            }
            continue
        ridge = ridge_sweep(X[tr], y[tr], X[te], y[te], n_classes, seed=seed)
        effective_nnz = effective_nonzero_nnz(W)
        arms[name] = {
            "acc": ridge["acc"],
            "train_acc": ridge["train_acc"],
            "train_test_gap": ridge["train_test_gap"],
            "selected_ridge": ridge["selected_ridge"],
            "ridge_curve": ridge["curve"],
            "seconds": time.time() - t0,
            "stored_nnz": int(W.nnz),
            "effective_nnz": effective_nnz,
            "ops_proxy": ops_proxy(effective_nnz, n_steps, len(I_list)),
            "readout_params": readout_params(X.shape[1], n_classes),
            "liveness": liveness,
            "spectrum": spec,
        }

    lif, _ = lifs["connectome_signed"]
    X, stats = reservoir_features(W_conn, I_list, lif, seed, input_ids=inputs)
    budget = readout_params(X.shape[1], n_classes)
    mlp_live = _check_alive(X, stats, "mlp_features")
    if mlp_live["alive"]:
        mlp_acc, mlp_params, mlp_info = mlp_baseline(
            X[tr], y[tr], X[te], y[te], n_classes, rng, param_budget=budget
        )
        arms["mlp"] = {"acc": mlp_acc, "params": mlp_params, "param_budget": budget,
                       **mlp_info, "liveness": mlp_live,
                       "note": "LSTM deferred (no torch)"}
    else:
        arms["mlp"] = {"acc": None, "param_budget": budget, "liveness": mlp_live,
                       "scoring_skipped": True, "note": "invalid connectome features"}
    chance = 1.0 / n_classes
    return {
        "seed": seed,
        "n": n,
        "nnz": nnz,
        "n_inputs": n_in,
        "chance": chance,
        "arms": arms,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="E1 reservoir vs nulls")
    ap.add_argument(
        "--allow-dead",
        action="store_true",
        help="record dead arms instead of raising. Diagnostic only: a run with this flag "
             "is a measurement of the dead baseline, never evidence for E1.",
    )
    ap.add_argument("--prefix", default="e1_pilot", help="result filename prefix")
    args = ap.parse_args(argv)

    cfg = load_cfg()
    cfg.setdefault("dynamics", {})["input_noise"] = cfg["dynamics"].get("input_noise", 0.35)
    # Always preserve each seed and close the claim gate when a guard fails.
    cfg.setdefault("harness_guards", {})["on_dead"] = "record"
    print("loading graph...", flush=True)
    g = load_graph(load_neurons=False)
    nodes = select_nodes(g, cfg["subgraph"]["n"])
    results = []
    for seed in cfg["seeds"]:
        print(f"seed {seed}...", flush=True)
        results.append(run_seed(g, nodes, cfg, seed))

    summary = {"provenance": provenance(), "config": cfg, "seeds": results, "aggregate": {}}
    for arm in cfg["arms"]:
        arm_rows = [r["arms"].get(arm, {}) for r in results]
        vals = [r["acc"] for r in arm_rows
                if r.get("acc") is not None and r.get("liveness", {}).get("alive", False)]
        all_valid = len(vals) == len(results) and len(results) == len(cfg["seeds"])
        if not all_valid:
            summary["aggregate"][arm] = {
                "mean_acc": None, "std": None, "ci95": None,
                "n_valid_diagnostic": len(vals), "n_planned": len(cfg["seeds"]),
                "invalid_seeds": [r["seed"] for r in results
                                  if not r["arms"].get(arm, {}).get("liveness", {}).get("alive", False)],
                "claim_metric_withheld": True,
            }
            continue
        arr = np.array(vals, dtype=np.float64)
        se = arr.std(ddof=1) / np.sqrt(len(arr)) if len(arr) > 1 else 0.0
        summary["aggregate"][arm] = {
            "mean_acc": float(arr.mean()),
            "std": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
            "ci95": float(1.96 * se),
            "n": len(arr),
        }
    agg = summary["aggregate"]
    chance = 1.0 / cfg["dynamics"]["n_classes"]
    live = {
        arm: all(r["arms"][arm].get("liveness", {}).get("alive", False) for r in results)
        for arm in ("connectome_signed", "connectome_abs", "er_null", "degree_shuffle")
    }
    summary["liveness"] = live
    measurements_valid = all(
        agg.get(arm, {}).get("claim_metric_withheld") is not True
        for arm in cfg["arms"]
    )
    conn = agg["connectome_signed"]["mean_acc"]
    er = agg["er_null"]["mean_acc"]
    sh = agg["degree_shuffle"]["mean_acc"]
    mlp = agg["mlp"]["mean_acc"]
    summary["task_validity"] = {
        "chance": chance,
        "reservoirs_alive": bool(all(live.values())),
        "measurements_valid": measurements_valid,
        "nulls_near_chance": bool(er < 0.55 and sh < 0.55) if measurements_valid else None,
        "not_ceiling": bool(max(er, sh, mlp, conn) < 0.95) if measurements_valid else None,
        "valid_for_claims": bool(measurements_valid and all(live.values())
                                  and er < 0.55 and sh < 0.55
                                  and max(er, sh, mlp, conn) < 0.95),
    }
    summary["pass_e1_preliminary"] = {
        "beats_both_nulls": bool(conn > er and conn > sh) if measurements_valid else None,
        "vs_mlp": float(conn - mlp) if measurements_valid else None,
        "blocked_by_invalid_task": not summary["task_validity"]["valid_for_claims"],
    }
    out = write_result(summary, prefix=args.prefix)
    print(json.dumps(summary["aggregate"], indent=2), flush=True)
    print("validity", summary["task_validity"], flush=True)
    print("WROTE", out, flush=True)


if __name__ == "__main__":
    main()
