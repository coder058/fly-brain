"""EXP-GLU-001: per-seed glutamate-polarity sensitivity."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import sparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import e1_reservoir as H
import null_ensemble as N
import polarity_arms as P
from flylab.dynamics import LIFParams, post_pre_from_pre_post
from flylab.graph import GRAPH_DIR, load_graph, load_meta
from flylab.polarity import load_policy, sign_series
from flylab.spectral import arm_spectrum, syn_scale_for_gain

EXPERIMENT_ID = "EXP-GLU-001"
PROTOCOL = ROOT / "experiments/results/EXP-GLU-001/protocol.md"
RESULTS = ROOT / "experiments/results/EXP-GLU-001"
SEEDS = tuple(range(12))  # SOURCE: frozen protocol.md
N_PROBES = 48  # SOURCE: frozen protocol.md
TRIALS_PER_CLASS = 60  # SOURCE: frozen protocol.md
TARGET_RATE = 0.002  # SOURCE: frozen protocol.md
RATE_MATCH_TOL = 0.10  # GUESS: preregistered instrument band; needs calibration data
GAIN_MIN = 0.05  # SOURCE: existing gain matcher bounds, frozen protocol.md
GAIN_MAX = 80.0  # SOURCE: existing gain matcher bounds, frozen protocol.md
POLICIES = ("glutamate_unknown", "glutamate_inhibitory", "glutamate_excitatory")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def derive_seed(protocol_hash: str, *labels) -> int:
    payload = protocol_hash + "|" + "|".join(map(str, labels))
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "little")


def write_json_once(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if path.exists() or tmp.exists():
        raise FileExistsError(f"refusing to overwrite artifact/checkpoint: {path}")
    with tmp.open("x", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_checkpoint(path: Path, protocol_hash: str, runner_hash: str):
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("protocol_sha256") != protocol_hash or data.get("runner_sha256") != runner_hash:
        raise RuntimeError(f"checkpoint provenance mismatch; refusing resume: {path}")
    return data


def live_report(X, stats, tag, cfg):
    guards = dict(cfg.get("harness_guards", {}))
    guards["on_dead"] = "record"
    return H.check_alive(X, stats, tag, guards)


def realised_rate(stats, n_trials: int, n_steps: int, n_pool: int) -> float:
    denominator = int(n_trials) * int(n_steps) * int(n_pool)
    return float(stats["pool_spikes"] / denominator) if denominator else 0.0


def ci95(values):
    x = np.asarray(values, dtype=float)
    if len(x) < 2:
        return 0.0
    return float(1.96 * x.std(ddof=1) / np.sqrt(len(x)))


def build_policy_graphs(g, nodes):
    mask = np.isin(g.src, nodes) & np.isin(g.dst, nodes)
    remap = -np.ones(g.n, dtype=np.int64)
    remap[nodes] = np.arange(len(nodes))
    src = remap[g.src[mask]]
    dst = remap[g.dst[mask]]
    w_abs = np.abs(g.weight[mask]).astype(np.float32)
    pre_body = g.body_ids[g.src[mask]]
    lut = P.nt_by_body(load_policy().get("nt_column", "consensus_nt"))
    nt = [lut.get(int(body), "unclear") for body in pre_body]
    counts = {str(k): int(v) for k, v in zip(
        *np.unique(np.asarray(nt, dtype=object).astype(str), return_counts=True)
    )}
    graphs, meta = {}, {}
    for policy in POLICIES:
        sign = sign_series(nt, policy).to_numpy().astype(np.float32)
        sw = sign * w_abs
        pre_post = sparse.csr_matrix((sw, (src, dst)), shape=(len(nodes), len(nodes)))
        W = post_pre_from_pre_post(pre_post).tocsr()
        effective_nnz = int(np.count_nonzero(sw))
        spectrum = arm_spectrum(W)
        graphs[policy] = W
        meta[policy] = {
            "policy": P.POLICIES[policy], "edges_total": int(len(sw)),
            "edges_excitatory": int((sign > 0).sum()),
            "edges_inhibitory": int((sign < 0).sum()),
            "edges_zeroed": int((sign == 0).sum()),
            "fraction_zeroed": float((sign == 0).mean()),
            "stored_nnz": int(W.nnz), "effective_nnz": effective_nnz,
            "ops_proxy_inflation": float(W.nnz / max(effective_nnz, 1)),
            "signed_weight_sum": float(sw.sum()), "spectrum": spectrum,
        }
    return graphs, meta, counts


def evaluate_seed(seed: int, cfg: dict, graphs: dict, meta: dict,
                  protocol_hash: str, runner_hash: str):
    n = int(next(iter(graphs.values())).shape[0])
    I_list, y, inputs, tr, te = N.make_trials_for(cfg, n, seed)
    n_pool = n - len(inputs)
    stride = max(1, len(I_list) // 20)
    I_match = [I_list[i] for i in range(0, len(I_list), stride)]
    n_steps = int(cfg["dynamics"]["n_steps"])
    train_inputs = [I_list[int(i)] for i in tr]
    test_inputs = [I_list[int(i)] for i in te]
    rows = {}
    for policy in POLICIES:
        W = graphs[policy]
        rho = meta[policy]["spectrum"]["rho_signed"]
        matched = P.match_gain(W, rho, I_match, inputs, cfg, seed, n_pool, TARGET_RATE)
        gain = float(matched["gain"])
        base = dict(cfg["dynamics"]["lif"])
        syn_scale = syn_scale_for_gain(rho, gain, base["tau_m"], base.get("dt", 1.0))
        lif = LIFParams(**{**base, "syn_scale": syn_scale})
        t0 = time.perf_counter()
        Xtr, sttr = H.reservoir_features(
            W, train_inputs, lif, derive_seed(protocol_hash, "train", policy, seed),
            input_ids=inputs, n_probes=N_PROBES,
        )
        Xte, stte = H.reservoir_features(
            W, test_inputs, lif, derive_seed(protocol_hash, "test", policy, seed),
            input_ids=inputs, n_probes=N_PROBES,
        )
        tr_live = live_report(Xtr, sttr, f"{policy}_train_seed{seed}", cfg)
        te_live = live_report(Xte, stte, f"{policy}_test_seed{seed}", cfg)
        train_rate = realised_rate(sttr, len(train_inputs), n_steps, n_pool)
        test_rate = realised_rate(stte, len(test_inputs), n_steps, n_pool)
        train_error = abs(train_rate - TARGET_RATE) / TARGET_RATE
        test_error = abs(test_rate - TARGET_RATE) / TARGET_RATE
        rate_match = bool(train_error <= RATE_MATCH_TOL and test_error <= RATE_MATCH_TOL)
        alive = bool(tr_live["alive"] and te_live["alive"])
        valid = bool(alive and rate_match)
        reason = []
        if not alive:
            reason.append("train/test liveness guard failed")
        if not rate_match:
            reason.append("train/test rate outside preregistered band")
        scored = H.ridge_sweep(
            Xtr, y[tr], Xte, y[te], cfg["dynamics"]["n_classes"], seed=seed
        ) if valid else None
        rows[policy] = {
            "seed": int(seed), "status": "LIVE" if valid else "MISSING",
            "alive": alive, "rate_match": rate_match,
            "gain": gain, "gain_match": matched,
            "syn_scale": float(syn_scale), "train_rate": train_rate,
            "test_rate": test_rate, "train_relative_rate_error": float(train_error),
            "test_relative_rate_error": float(test_error),
            "train_liveness": tr_live, "test_liveness": te_live,
            "acc": scored["acc"] if scored else None,
            "train_acc": scored["train_acc"] if scored else None,
            "train_test_gap": scored["train_test_gap"] if scored else None,
            "selected_ridge": scored["selected_ridge"] if scored else None,
            "reason": "; ".join(reason) if reason else None,
            "effective_nnz": meta[policy]["effective_nnz"],
            "wall_seconds": time.perf_counter() - t0,
        }
    return {
        "experiment_id": EXPERIMENT_ID, "seed": int(seed),
        "policies": rows, "n_trials_per_class": TRIALS_PER_CLASS,
        "n_probes": N_PROBES, "target_rate": TARGET_RATE,
        "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
    }


def aggregate(root: Path, protocol_hash: str, runner_hash: str):
    rows = []
    for seed in SEEDS:
        p = root / f"seed_{seed:04d}.json"
        if p.exists():
            rows.append(read_checkpoint(p, protocol_hash, runner_hash))
    all_valid = len(rows) == len(SEEDS) and all(
        all(x["status"] == "LIVE" for x in row["policies"].values()) for row in rows
    )
    arms = {}
    for policy in POLICIES:
        vals = [row["policies"][policy]["acc"] for row in rows
                if row["policies"][policy]["acc"] is not None]
        arms[policy] = {
            "valid_seed_count": len(vals),
            "mean_acc": float(np.mean(vals)) if all_valid else None,
            "ci95": ci95(vals) if all_valid else None,
            "per_seed_acc": vals if all_valid else [],
            "claim_metric_withheld": not all_valid,
        }
    deltas = {}
    ref = POLICIES[0]
    for policy in POLICIES[1:]:
        if all_valid:
            diff = np.asarray([row["policies"][policy]["acc"] - row["policies"][ref]["acc"]
                               for row in rows], dtype=float)
            deltas[f"{policy}_minus_{ref}"] = {
                "mean_diff": float(diff.mean()), "ci95_diff": ci95(diff),
                "per_seed_diff": diff.tolist(),
            }
        else:
            deltas[f"{policy}_minus_{ref}"] = {"mean_diff": None,
                                                "ci95_diff": None,
                                                "claim_metric_withheld": True}
    return {
        "experiment_id": EXPERIMENT_ID,
        "status": "COMPLETE_VALID" if all_valid else "COMPLETE_METRIC_WITHHELD",
        "scientific_result": bool(all_valid), "seeds_written": len(rows),
        "expected_seeds": len(SEEDS), "arms": arms,
        "deltas_vs_glutamate_unknown": deltas,
        "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
    }


def make_root():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rev = H.provenance().get("git_rev", "unknown")
    root = RESULTS / f"glu001_{stamp}_{rev}"
    root.mkdir(parents=True)
    return root


def check_root(path: Path):
    resolved = path.resolve()
    if RESULTS.resolve() not in resolved.parents or not resolved.name.startswith("glu001_"):
        raise ValueError(f"run root must be a glu001_* directory below {RESULTS.resolve()}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def run(run_root: Path):
    cfg = H.load_cfg()
    cfg["dynamics"] = dict(cfg["dynamics"])
    cfg["dynamics"]["n_trials_per_class"] = TRIALS_PER_CLASS
    cfg.setdefault("harness_guards", {})["on_dead"] = "record"
    protocol_hash = sha256_file(PROTOCOL)
    runner_hash = sha256_file(Path(__file__))
    root = check_root(run_root)
    g = load_graph(load_neurons=True)
    nodes = H.select_nodes(g, cfg["subgraph"]["n"])
    graphs, meta, nt_counts = build_policy_graphs(g, nodes)
    init = root / "run_started.json"
    if not init.exists():
        write_json_once(init, {
            "experiment_id": EXPERIMENT_ID,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
            "config_sha256": sha256_file(H.CFG_PATH),
            "graph_meta": load_meta(GRAPH_DIR / "graph_meta.json"),
            "graph_sha256": {name: sha256_file(GRAPH_DIR / name) for name in
                             ("csr_unsigned.npz", "csc_unsigned.npz", "coo_signed.npz")},
            "policies": list(POLICIES), "seeds": list(SEEDS),
            "n_probes": N_PROBES, "n_trials_per_class": TRIALS_PER_CLASS,
            "target_rate": TARGET_RATE, "gain_bounds": [GAIN_MIN, GAIN_MAX],
            "nt_column": load_policy().get("nt_column", "consensus_nt"),
            "nt_counts": nt_counts, "arms": meta,
        })
    started = time.perf_counter()
    for seed in SEEDS:
        out = root / f"seed_{seed:04d}.json"
        if read_checkpoint(out, protocol_hash, runner_hash) is None:
            write_json_once(out, evaluate_seed(seed, cfg, graphs, meta, protocol_hash, runner_hash))
            print(json.dumps({"seed": seed, "seconds": round(time.perf_counter() - started, 2)}), flush=True)
    summary = aggregate(root, protocol_hash, runner_hash)
    summary["seconds"] = time.perf_counter() - started
    write_json_once(root / "summary.json", summary)
    print(json.dumps({"run_root": str(root), **summary}, indent=2), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-root", type=Path)
    args = ap.parse_args(argv)
    if not PROTOCOL.is_file():
        ap.error(f"missing frozen preregistration: {PROTOCOL}")
    run(args.run_root or make_root())


if __name__ == "__main__":
    main()
