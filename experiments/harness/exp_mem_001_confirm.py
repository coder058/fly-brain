"""Preregistered post-INST EXP-MEM-001 runner; preserves the exploratory pilot."""
from __future__ import annotations

import argparse
import copy
import contextlib
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.stats import norm, t

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import e1_reservoir as H
from flylab.dynamics import LIFParams
from flylab.graph import induced_subgraph, load_graph
from flylab.nulls import (degree_preserving_null, er_graph, ring_lattice,
                          weight_permutation_null)
from flylab.spectral import spectral_radius, syn_scale_for_gain
from memory_task import combine_split_liveness, delay_line_recall, simulate_terminal_features

PROTOCOL = ROOT / "experiments/results/EXP-MEM-001/protocol.md"
RESULTS = ROOT / "experiments/results/EXP-MEM-001"
DELAYS = (10, 25, 50, 100, 250, 500)  # SOURCE: frozen protocol.md
N_NODES = 500  # SOURCE: frozen protocol.md
N_PROBES = 48  # SOURCE: frozen protocol.md
N_INPUTS = 50  # SOURCE: 10% of 500, frozen protocol.md
INPUT_GROUP_SIZE = 25  # SOURCE: frozen protocol.md, balanced two-channel map
PILOT_SEEDS = tuple(range(100, 106))  # SOURCE: frozen sizing plan
CONFIRM_SEEDS = tuple(range(12))  # SOURCE: human minimum / frozen protocol
EXTENSION_SEEDS = tuple(range(12, 24))  # SOURCE: frozen one-time expansion
NULL_REPLICATES = 2  # SOURCE: frozen protocol; >=20 draws/type in 12-seed tranche
TRIALS_CONFIRM_PER_CLASS = 100  # SOURCE: frozen protocol
TRIALS_PILOT_PER_CLASS = 30  # SOURCE: frozen sizing plan
TRIALS_SMOKE_PER_CLASS = 4  # SOURCE: frozen smoke plan
CALIBRATION_LAG = 100  # SOURCE: frozen protocol
CALIBRATION_TRIALS_PER_CLASS = 10  # SOURCE: frozen protocol
GAIN_GRID_MIN = 0.125  # UNCALIBRATED GUESS: preregistered calibration lower bound only
GAIN_GRID_MAX = 64.0  # UNCALIBRATED GUESS: preregistered calibration upper bound only
GAIN_GRID_SIZE = 64  # UNCALIBRATED GUESS: preregistered calibration resolution only
RATE_MATCH_TOL = 0.10  # UNCALIBRATED GUESS: rate-matching tolerance
EFFECT_MARGIN = 0.05  # UNCALIBRATED GUESS: practical equivalence margin
RNN_HIDDEN = 8  # SOURCE: frozen protocol; exact 98-parameter budget match
RNN_LR = 0.01  # UNCALIBRATED GUESS: CPU Elman training rate
RNN_MAX_EPOCHS = 50  # UNCALIBRATED GUESS: CPU training budget
RNN_PATIENCE = 10  # UNCALIBRATED GUESS: validation early-stop patience
RNN_INIT_STD = 0.05  # UNCALIBRATED GUESS: small tanh initialization scale
RIDGE_VAL_FRACTION = 0.20  # SOURCE: frozen protocol; training-only validation
LIVENESS_MIN_UNIQUE = 2  # SOURCE: binary-task minimum distinct feature rows
ARM_TYPES = ("connectome", "dp", "weight_perm", "er", "ring")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def derive_seed(protocol_hash: str, *labels) -> int:
    payload = protocol_hash + "|" + "|".join(map(str, labels))
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "little")


def rng_for(protocol_hash: str, *labels) -> np.random.Generator:
    return np.random.default_rng(derive_seed(protocol_hash, *labels))


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
    if path.exists():
        raise FileExistsError(f"target appeared during write: {path}")
    os.replace(tmp, path)


def read_checkpoint(path: Path, protocol_hash: str, runner_hash: str):
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if (data.get("protocol_sha256") != protocol_hash
            or data.get("runner_sha256") != runner_hash):
        raise RuntimeError(f"checkpoint provenance mismatch; refusing resume: {path}")
    return data


def make_trials(n, cue0, cue1, trials_per_class, lag, cue_amplitude,
                protocol_hash, seed, split):
    rng = rng_for(protocol_hash, "task", seed, split, lag)
    y = np.repeat(np.array([0, 1], dtype=np.int64), int(trials_per_class))
    rng.shuffle(y)
    drive = np.zeros((len(y), int(lag) + 1, n), dtype=np.float32)
    idx0 = np.flatnonzero(y == 0)
    idx1 = np.flatnonzero(y == 1)
    drive[idx0[:, None], 0, np.asarray(cue0)[None, :]] = cue_amplitude
    drive[idx1[:, None], 0, np.asarray(cue1)[None, :]] = cue_amplitude
    return drive, y


def live_report(X, stats, tag, quiet=False):
    guards = dict(H.load_cfg().get("harness_guards", {}))
    guards.update({"on_dead": "record", "min_unique_feature_rows": LIVENESS_MIN_UNIQUE})
    if quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            return H.check_alive(X, stats, tag, guards)
    return H.check_alive(X, stats, tag, guards)


def fit_ridge_train_only(Xtr, ytr, Xte, yte, seed_key, stage, seed, lag):
    rng = rng_for(seed_key, "ridge-validation", stage, seed, lag)
    sub_idx, val_idx = [], []
    for cls in (0, 1):
        idx = np.flatnonzero(ytr == cls)
        rng.shuffle(idx)
        n_val = max(1, int(round(len(idx) * RIDGE_VAL_FRACTION)))
        val_idx.extend(idx[:n_val].tolist())
        sub_idx.extend(idx[n_val:].tolist())
    curve = []
    for ridge in H.RIDGE_GRID:
        wv = H.fit_readout(Xtr[sub_idx], ytr[sub_idx], 2, ridge=ridge)
        curve.append((H.accuracy(ytr[val_idx], H.predict(wv, Xtr[val_idx])), float(ridge)))
    best_val, best_ridge = max(curve, key=lambda item: (item[0], -item[1]))
    w = H.fit_readout(Xtr, ytr, 2, ridge=best_ridge)
    yhat = H.predict(w, Xte)
    return {
        "accuracy": float(H.accuracy(yte, yhat)),
        "train_accuracy": float(H.accuracy(ytr, H.predict(w, Xtr))),
        "selected_ridge": best_ridge,
        "validation_accuracy": float(best_val),
        "selection": "train-only stratified validation; test evaluated once",
        "test_predictions": np.asarray(yhat, dtype=int).tolist(),
    }


def softmax_loss(logits, y):
    z = logits - logits.max(axis=1, keepdims=True)
    ez = np.exp(z)
    p = ez / ez.sum(axis=1, keepdims=True)
    loss = -np.log(np.maximum(p[np.arange(len(y)), y], np.finfo(float).tiny)).mean()
    grad = p
    grad[np.arange(len(y)), y] -= 1.0
    grad /= len(y)
    return float(loss), grad


def rnn_forward(params, x0, steps):
    batch = len(x0)
    hidden = params["win"].shape[1]
    states = np.zeros((steps + 1, batch, hidden), dtype=np.float64)
    zero_drive = np.zeros_like(x0)
    for ti in range(steps):
        drive = x0 if ti == 0 else zero_drive
        states[ti + 1] = np.tanh(drive @ params["win"] + states[ti] @ params["wrec"])
    logits = states[-1] @ params["wout"] + params["bout"]
    return logits, states


def rnn_loss_grads(params, x0, y, steps):
    logits, states = rnn_forward(params, x0, steps)
    loss, dlogits = softmax_loss(logits, y)
    grads = {
        "wout": states[-1].T @ dlogits,
        "bout": dlogits.sum(axis=0),
        "win": np.zeros_like(params["win"]),
        "wrec": np.zeros_like(params["wrec"]),
    }
    dh = dlogits @ params["wout"].T
    for ti in range(steps - 1, -1, -1):
        h = states[ti + 1]
        da = dh * (1.0 - h * h)
        if ti == 0:
            grads["win"] = x0.T @ da
        grads["wrec"] += states[ti].T @ da
        dh = da @ params["wrec"].T
    return loss, grads


def train_elman(ytr, yval, lag, protocol_hash, seed, stage):
    rng = rng_for(protocol_hash, "elman-init", stage, seed, lag)
    xtr = np.eye(2, dtype=np.float64)[ytr]
    xval = np.eye(2, dtype=np.float64)[yval]
    h = RNN_HIDDEN
    params = {
        "win": rng.normal(0.0, RNN_INIT_STD, size=(2, h)),
        "wrec": rng.normal(0.0, RNN_INIT_STD, size=(h, h)),
        "wout": rng.normal(0.0, RNN_INIT_STD, size=(h, 2)),
        "bout": np.zeros(2, dtype=np.float64),
    }
    best = copy.deepcopy(params)
    best_loss = float("inf")
    stale = 0
    m = {k: np.zeros_like(v) for k, v in params.items()}
    v = {k: np.zeros_like(val) for k, val in params.items()}
    beta1, beta2, eps = 0.9, 0.999, 1e-8  # SOURCE: Adam defaults (Kingma & Ba, 2014)
    start = time.perf_counter()
    for epoch in range(1, RNN_MAX_EPOCHS + 1):
        _, grads = rnn_loss_grads(params, xtr, ytr, lag + 1)
        for name in params:
            m[name] = beta1 * m[name] + (1.0 - beta1) * grads[name]
            v[name] = beta2 * v[name] + (1.0 - beta2) * grads[name] ** 2
            mhat = m[name] / (1.0 - beta1 ** epoch)
            vhat = v[name] / (1.0 - beta2 ** epoch)
            params[name] -= RNN_LR * mhat / (np.sqrt(vhat) + eps)
        val_logits, _ = rnn_forward(params, xval, lag + 1)
        val_loss, _ = softmax_loss(val_logits, yval)
        if val_loss < best_loss:
            best_loss = val_loss
            best = copy.deepcopy(params)
            stale = 0
        else:
            stale += 1
            if stale >= RNN_PATIENCE:
                break
    return best, {"epochs": epoch, "best_validation_loss": best_loss,
                  "wall_seconds": time.perf_counter() - start,
                  "trainable_params": int(2*h + h*h + h*2 + 2),
                  "parameter_match_target": int(48*2 + 2),
                  "model": "CPU tanh Elman RNN (not LSTM/GRU)"}


def predict_elman(params, y, lag):
    x = np.eye(2, dtype=np.float64)[y]
    logits, _ = rnn_forward(params, x, lag + 1)
    return np.argmax(logits, axis=1)


def rnn_train_test(ytr, yte, protocol_hash, stage, seed, lag):
    rng = rng_for(protocol_hash, "elman-validation", stage, seed, lag)
    sub_idx, val_idx = [], []
    for cls in (0, 1):
        idx = np.flatnonzero(ytr == cls)
        rng.shuffle(idx)
        n_val = max(1, int(round(len(idx) * RIDGE_VAL_FRACTION)))
        val_idx.extend(idx[:n_val].tolist())
        sub_idx.extend(idx[n_val:].tolist())
    params, info = train_elman(ytr[sub_idx], ytr[val_idx], lag, protocol_hash, seed, stage)
    pred = predict_elman(params, yte, lag)
    info["accuracy"] = float(H.accuracy(yte, pred))
    info["test_predictions"] = np.asarray(pred, dtype=int).tolist()
    info["operations_proxy"] = int((lag + 1) * len(ytr) * (2 * RNN_HIDDEN * (2 + RNN_HIDDEN + 2)))
    return info


def create_graph_variants(graph, nodes, protocol_hash, task_seed, replicates):
    A, _ = induced_subgraph(graph, nodes)
    coo = A.tocoo()
    active = coo.data != 0
    src, dst, weights = coo.row[active], coo.col[active], coo.data[active].astype(np.float32)
    n = len(nodes)
    active_edges = len(weights)
    Wconn = sparse.csr_matrix((weights, (dst, src)), shape=(n, n))
    Wconn.eliminate_zeros()
    variants = [{
        "name": "connectome-0", "arm": "connectome", "replicate": 0,
        "W": Wconn, "diagnostics": {"active_edges": int(Wconn.nnz)},
    }]
    for arm in ("dp", "weight_perm", "er", "ring"):
        for rep in range(replicates):
            rng = rng_for(protocol_hash, "null-graph", task_seed, arm, rep)
            if arm == "dp":
                W, diag = degree_preserving_null(src, dst, weights, n, rng)
            elif arm == "weight_perm":
                W, diag = weight_permutation_null(src, dst, weights, n, rng)
            elif arm == "er":
                W = er_graph(n, active_edges, rng, excitatory_only=False)
                diag = {"n_edges_out": int(W.nnz), "weight_law": "random_sign_uniform_1_10"}
            else:
                W = ring_lattice(n, active_edges, rng, excitatory_only=True)
                diag = {"n_edges_out": int(W.nnz), "weight_law": "positive_uniform_1_10"}
            W = W.tocsr()
            W.eliminate_zeros()
            if W.nnz != active_edges:
                raise RuntimeError(f"{arm} edge budget mismatch: {W.nnz} vs {active_edges}")
            variants.append({
                "name": f"{arm}-{rep}", "arm": arm, "replicate": rep,
                "W": W, "diagnostics": diag,
            })
    if len({v["W"].nnz for v in variants}) != 1:
        raise RuntimeError("structural arms do not share the active edge budget")
    return variants, {"stored_subgraph_edges": int(A.nnz),
                      "active_nonzero_edges": int(active_edges), "n_nodes": int(n)}


def common_rate_target(calibrations):
    primary = [c for c in calibrations if c["arm"] == "connectome" or c["arm"] == "dp"]
    valid = {c["name"]: [x for x in c["candidates"] if x["alive"] and x["rate"] > 0]
             for c in primary}
    if any(not v for v in valid.values()):
        return None, {}
    targets = sorted({float(x["rate"]) for vals in valid.values() for x in vals})
    def objective(target):
        errors = []
        for vals in valid.values():
            best = min(vals, key=lambda x: abs(x["rate"] - target) / target)
            errors.append(abs(best["rate"] - target) / target)
        return max(errors)
    target = min(targets, key=lambda r: (objective(r), r))
    selected = {}
    for cal in calibrations:
        live = [x for x in cal["candidates"] if x["alive"] and x["rate"] > 0]
        if live:
            selected[cal["name"]] = min(live, key=lambda x: abs(x["rate"] - target) / target)
        else:
            selected[cal["name"]] = min(cal["candidates"], key=lambda x: abs(x["rate"] - target))
    primary_ok = all(
        selected[c["name"]]["alive"]
        and abs(selected[c["name"]]["rate"] - target) / target <= RATE_MATCH_TOL
        for c in primary
    )
    return target, {"selected": selected, "primary_rate_match_ok": bool(primary_ok),
                    "primary_max_relative_error": float(objective(target))}


def calibrate_variants(variants, cfg, cue0, cue1, inputs, probes, protocol_hash, stage, seed):
    base = dict(cfg["dynamics"]["lif"])
    lif0 = LIFParams(**base)
    amp = (lif0.v_th - lif0.v_rest) * lif0.tau_m / (lif0.r * lif0.dt)
    drive, _ = make_trials(
        N_NODES,
        cue0, cue1, CALIBRATION_TRIALS_PER_CLASS, CALIBRATION_LAG, amp,
        protocol_hash, seed, "calibration",
    )
    # GUESS bounds/resolution are preregistered and never selected using accuracy.
    gains = np.geomspace(GAIN_GRID_MIN, GAIN_GRID_MAX, GAIN_GRID_SIZE)
    calibrations = []
    for variant in variants:
        W = variant["W"]
        rho_abs = spectral_radius(W, signed=False)
        candidates = []
        for gain in gains:
            lif = LIFParams(**{
                **base,
                "syn_scale": syn_scale_for_gain(
                    rho_abs, float(gain), lif0.tau_m, lif0.dt, lif0.r
                ),
            })
            X, stats = simulate_terminal_features(
                W, drive, lif, inputs, probes,
                derive_seed(protocol_hash, "calibration-init", stage, seed),
            )
            live = live_report(X, stats, variant["name"], quiet=True)
            denominator = len(drive) * drive.shape[1] * stats["pool_size"]
            rate = float(stats["pool_spikes"] / denominator) if denominator else 0.0
            candidates.append({
                "gain": float(gain), "syn_scale": float(lif.syn_scale),
                "rate": rate, "alive": bool(live["alive"]), "liveness": live,
            })
        calibrations.append({
            "name": variant["name"], "arm": variant["arm"],
            "replicate": variant["replicate"], "rho_abs": float(rho_abs),
            "candidates": candidates,
        })
    target, choice = common_rate_target(calibrations)
    selected = choice.get("selected", {})
    for cal in calibrations:
        cal["selected"] = selected.get(cal["name"])
        cal["relative_rate_error"] = (
            abs(cal["selected"]["rate"] - target) / target
            if target and cal["selected"] else None
        )
    meta = {
        "calibration_delay": CALIBRATION_LAG,
        "trials_per_class": CALIBRATION_TRIALS_PER_CLASS,
        "common_target_rate": target,
        "primary_rate_match_ok": choice.get("primary_rate_match_ok", False),
        "primary_max_relative_error": choice.get("primary_max_relative_error"),
        "variants": calibrations,
    }
    return meta


def make_input_map(n, protocol_hash, task_seed):
    rng = rng_for(protocol_hash, "input-map", task_seed)
    inputs = np.sort(rng.choice(n, size=N_INPUTS, replace=False))
    cue0, cue1 = inputs[:INPUT_GROUP_SIZE], inputs[INPUT_GROUP_SIZE:]
    probe_seed = derive_seed(protocol_hash, "probe-map", task_seed) % (2**32)
    probes, _ = H.probe_set(n, inputs, N_PROBES, int(probe_seed))
    if np.intersect1d(inputs, probes).size:
        raise RuntimeError("input/probe leak")
    return inputs, cue0, cue1, probes


def run_cell(variants, calibration, cfg, inputs, cue0, cue1, probes,
             protocol_hash, runner_hash, stage, seed, lag, trials_per_class,
             run_rnn):
    base = dict(cfg["dynamics"]["lif"])
    lif0 = LIFParams(**base)
    cue_amp = (lif0.v_th - lif0.v_rest) * lif0.tau_m / (lif0.r * lif0.dt)
    train_drive, ytr = make_trials(
        N_NODES, cue0, cue1, trials_per_class, lag, cue_amp,
        protocol_hash, seed, f"{stage}-train",
    )
    test_drive, yte = make_trials(
        N_NODES, cue0, cue1, trials_per_class, lag, cue_amp,
        protocol_hash, seed, f"{stage}-test",
    )
    results = {}
    started = time.perf_counter()
    for variant in variants:
        selected = next(
            v["selected"] for v in calibration["variants"] if v["name"] == variant["name"]
        )
        if selected is None:
            results[variant["name"]] = {
                "arm": variant["arm"], "replicate": variant["replicate"],
                "alive": False, "accuracy": None, "reason": "no live calibration gain",
            }
            continue
        lif = LIFParams(**{**base, "syn_scale": selected["syn_scale"]})
        w0, c0 = time.perf_counter(), time.process_time()
        Xtr, sttr = simulate_terminal_features(
            variant["W"], train_drive, lif, inputs, probes,
            derive_seed(protocol_hash, "sim-init", stage, seed, lag, "train"),
        )
        Xte, stte = simulate_terminal_features(
            variant["W"], test_drive, lif, inputs, probes,
            derive_seed(protocol_hash, "sim-init", stage, seed, lag, "test"),
        )
        sumstats = {
            "pool_spikes": sttr["pool_spikes"] + stte["pool_spikes"],
            "probe_spikes": sttr["probe_spikes"] + stte["probe_spikes"],
        }
        summary = live_report(np.concatenate([Xtr, Xte]), sumstats, variant["name"])
        tr_live = live_report(Xtr, sttr, f"{variant['name']}_train")
        te_live = live_report(Xte, stte, f"{variant['name']}_test")
        live = combine_split_liveness(summary, tr_live, te_live)
        scored = None
        if live["alive"]:
            scored = fit_ridge_train_only(
                Xtr, ytr, Xte, yte, protocol_hash, stage, seed, lag
            )
        nsteps = lag + 1
        denom_tr = len(ytr) * nsteps * sttr["pool_size"]
        denom_te = len(yte) * nsteps * stte["pool_size"]
        results[variant["name"]] = {
            "arm": variant["arm"], "replicate": variant["replicate"],
            "alive": bool(live["alive"]), "liveness": live,
            "train_rate": float(sttr["pool_spikes"] / denom_tr),
            "test_rate": float(stte["pool_spikes"] / denom_te),
            "calibration_rate": selected["rate"],
            "rate_relative_error": calibration["common_target_rate"] and
                abs(selected["rate"] - calibration["common_target_rate"]) /
                calibration["common_target_rate"],
            "gain": selected["gain"], "syn_scale": selected["syn_scale"],
            "active_edges": int(variant["W"].nnz),
            "accuracy": scored["accuracy"] if scored else None,
            "train_accuracy": scored["train_accuracy"] if scored else None,
            "selected_ridge": scored["selected_ridge"] if scored else None,
            "validation_accuracy": scored["validation_accuracy"] if scored else None,
            "test_predictions": scored["test_predictions"] if scored else None,
            "wall_seconds": time.perf_counter() - w0,
            "cpu_seconds": time.process_time() - c0,
            "synapse_step_ops": int(variant["W"].nnz * nsteps * (len(ytr) + len(yte))),
        }
    fifo = np.asarray([delay_line_recall(int(y), lag, max(DELAYS)) for y in yte])
    no_network = np.zeros_like(yte)
    rnn = None
    if run_rnn:
        rnn = rnn_train_test(ytr, yte, protocol_hash, stage, seed, lag)
    return {
        "experiment_id": "EXP-MEM-001", "stage": stage, "seed": int(seed),
        "lag_steps": int(lag), "trials_per_class_per_split": int(trials_per_class),
        "input_group_0": cue0.tolist(), "input_group_1": cue1.tolist(),
        "probe_ids": probes.tolist(), "cue_amplitude": float(cue_amp),
        "external_input_after_onset_nonzero_count": int(np.count_nonzero(test_drive[:, 1:, :])),
        "fifo_accuracy": float(H.accuracy(yte, fifo)),
        "no_network_accuracy": float(H.accuracy(yte, no_network)),
        "labels_test": yte.astype(int).tolist(), "results": results,
        "elman_rnn": rnn,
        "cell_wall_seconds": time.perf_counter() - started,
        "protocol_sha256": sha256_file(PROTOCOL),
        "runner_sha256": runner_hash,
    }


def make_run_root():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rev = H.provenance().get("git_rev", "unknown")
    root = RESULTS / f"post_inst_{stamp}_{rev}"
    suffix = 0
    candidate = root
    while candidate.exists():
        suffix += 1
        candidate = RESULTS / f"post_inst_{stamp}_{rev}_{suffix}"
    candidate.mkdir(parents=True)
    return candidate


def check_run_root(path):
    resolved = path.resolve()
    allowed = RESULTS.resolve()
    if allowed not in resolved.parents or not resolved.name.startswith("post_inst_"):
        raise ValueError(f"run root must be a new post_inst_* directory below {allowed}")
    if not resolved.exists():
        resolved.mkdir(parents=True)
    return resolved


def t_interval(values):
    x = np.asarray(values, dtype=float)
    if len(x) < 2:
        return {"n": int(len(x)), "mean": float(np.mean(x)) if len(x) else None,
                "ci95_low": None, "ci95_high": None}
    mean = float(x.mean())
    se = float(x.std(ddof=1) / np.sqrt(len(x)))
    half = float(t.ppf(0.975, len(x) - 1) * se)
    return {"n": int(len(x)), "mean": mean, "ci95_low": mean - half, "ci95_high": mean + half}


def normalized_auc(curve):
    vals = np.asarray([curve[d] for d in DELAYS], dtype=float)
    return float(np.trapz(vals, np.asarray(DELAYS, dtype=float)) / (DELAYS[-1] - DELAYS[0]))


def aggregate_stage(stage_dir, stage, seeds, runner_hash, protocol_hash):
    cells = {}
    for seed in seeds:
        cells[seed] = {}
        for lag in ( (10, 100) if stage == "smoke" else DELAYS ):
            p = stage_dir / f"seed_{seed:04d}_lag_{lag:03d}.json"
            if p.exists():
                cells[seed][lag] = read_checkpoint(p, protocol_hash, runner_hash)
    if stage == "smoke":
        return {"stage": stage, "cells_written": sum(len(x) for x in cells.values()),
                "cells": cells}
    arm_curves, invalid = {}, []
    network_names = sorted({name for sd in cells.values() for row in sd.values()
                            for name in row["results"]})
    for arm in network_names:
        arm_curves[arm] = {}
        for lag in DELAYS:
            seed_acc = []
            for seed in seeds:
                row = cells.get(seed, {}).get(lag)
                if not row:
                    continue
                reps = [r["accuracy"] for r in row["results"].values()
                        if r["arm"] == arm and r["accuracy"] is not None]
                if reps:
                    seed_acc.append((seed, float(np.mean(reps))))
            arm_curves[arm][lag] = t_interval([a for _, a in seed_acc])
            arm_curves[arm][lag]["by_seed"] = {str(s): a for s, a in seed_acc}
    auc_by_arm = {}
    for arm, lag_rows in arm_curves.items():
        complete = {int(s): {d: lag_rows[d]["by_seed"].get(str(s)) for d in DELAYS}
                    for s in seeds}
        auc_by_arm[arm] = {
            str(s): normalized_auc(v) for s, v in complete.items()
            if all(x is not None for x in v.values())
        }
    paired = []
    for seed in seeds:
        c = auc_by_arm.get("connectome-0", {}).get(str(seed))
        dp = [v[str(seed)] for k, v in auc_by_arm.items()
              if k.startswith("dp-") and str(seed) in v]
        if c is not None and len(dp) == NULL_REPLICATES:
            paired.append({"seed": int(seed), "difference": float(c - np.mean(dp))})
    interval = t_interval([x["difference"] for x in paired])
    all_liveness = True
    all_rate_match = True
    for seed in seeds:
        cp = stage_dir / f"calibration_seed_{seed:04d}.json"
        if cp.exists():
            cdata = read_checkpoint(cp, protocol_hash, runner_hash)
            all_rate_match &= bool(cdata.get("primary_rate_match_ok"))
        for lag in DELAYS:
            row = cells.get(seed, {}).get(lag)
            if row is None:
                all_liveness = False
                continue
            for res in row["results"].values():
                if res["arm"] in ARM_TYPES and not res.get("alive"):
                    all_liveness = False
    ci_lo, ci_hi = interval["ci95_low"], interval["ci95_high"]
    if not all_liveness or not all_rate_match:
        status = "INVALIDATED"
    elif ci_lo is None or ci_hi is None:
        status = "INCONCLUSIVE"
    elif ci_lo > EFFECT_MARGIN:
        status = "INTERPRETABLE_CONNECTOME_HIGHER"
    elif ci_hi < -EFFECT_MARGIN:
        status = "INTERPRETABLE_CONNECTOME_LOWER"
    elif ci_lo >= -EFFECT_MARGIN and ci_hi <= EFFECT_MARGIN:
        status = "INTERPRETABLE_APPROXIMATE_TIE"
    else:
        status = "INCONCLUSIVE"
    summary = {
        "experiment_id": "EXP-MEM-001", "stage": stage,
        "status": status, "n_task_seeds": len(seeds),
        "delays": list(DELAYS), "curve_by_arm": arm_curves,
        "normalized_auc_by_arm_by_seed": auc_by_arm,
        "primary_connectome_minus_dp_auc": interval,
        "paired_seed_differences": paired,
        "all_network_liveness_passed": bool(all_liveness),
        "all_primary_rate_matches_passed": bool(all_rate_match),
        "equivalence_margin": EFFECT_MARGIN,
        "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
    }
    if stage == "sizing" and all_liveness and all_rate_match and len(paired) >= 2:
        sd = float(np.std([x["difference"] for x in paired], ddof=1))
        n_raw = int(np.ceil(((norm.ppf(0.975) + norm.ppf(0.80)) * sd / EFFECT_MARGIN) ** 2))
        n_plan = 12 if n_raw <= 12 else 24
        summary["pilot_power_sizing"] = {
            "paired_difference_sd": sd, "n_raw": n_raw, "n_planned": n_plan,
            "underpowered_at_cap": bool(n_raw > 24),
            "formula": "ceil(((z_.975+z_.80)*pilot_sd/0.05)^2)",
            "pilot_only_not_claim_evidence": True,
        }
    return summary


def run_stage(stage, run_root, cfg):
    protocol_hash = sha256_file(PROTOCOL)
    runner_hash = sha256_file(Path(__file__))
    run_root = check_run_root(run_root)
    stage_dir = run_root / stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    if stage == "smoke":
        seeds, trials, lags, reps, run_rnn = (0,), TRIALS_SMOKE_PER_CLASS, (10, 100), 1, False
        arms = ("connectome", "dp")
    elif stage == "sizing":
        seeds, trials, lags, reps, run_rnn = PILOT_SEEDS, TRIALS_PILOT_PER_CLASS, DELAYS, NULL_REPLICATES, False
        arms = ARM_TYPES
    elif stage == "confirm":
        seeds, trials, lags, reps, run_rnn = CONFIRM_SEEDS, TRIALS_CONFIRM_PER_CLASS, DELAYS, NULL_REPLICATES, True
        arms = ARM_TYPES
    elif stage == "extension":
        seeds, trials, lags, reps, run_rnn = EXTENSION_SEEDS, TRIALS_CONFIRM_PER_CLASS, DELAYS, NULL_REPLICATES, True
        arms = ARM_TYPES
    else:
        raise ValueError(stage)

    graph = load_graph(load_neurons=False)
    nodes = H.select_nodes(graph, N_NODES)
    graph_sha = {
        name: sha256_file(ROOT / "data/derived/graph" / name)
        for name in ("csr_unsigned.npz", "csc_unsigned.npz", "coo_signed.npz")
    }
    cfg_hash = sha256_file(H.CFG_PATH)
    stage_start = stage_dir / "stage_started.json"
    if not stage_start.exists():
        write_json_once(stage_start, {
            "stage": stage, "started_utc": datetime.now(timezone.utc).isoformat(),
            "experiment_id": "EXP-MEM-001", "protocol_sha256": protocol_hash,
            "runner_sha256": runner_hash, "config_sha256": cfg_hash,
            "graph_sha256": graph_sha,
        })

    for seed in seeds:
        inputs, cue0, cue1, probes = make_input_map(N_NODES, protocol_hash, seed)
        variants, graph_diag = create_graph_variants(
            graph, nodes, protocol_hash, seed, reps
        )
        if stage == "smoke":
            variants = [v for v in variants if v["arm"] in arms]
        cal_path = stage_dir / f"calibration_seed_{seed:04d}.json"
        caldata = read_checkpoint(cal_path, protocol_hash, runner_hash)
        if caldata is None:
            calibration = calibrate_variants(
                variants, cfg, cue0, cue1, inputs, probes, protocol_hash, stage, seed
            )
            caldata = {
                "experiment_id": "EXP-MEM-001", "stage": stage, "seed": int(seed),
                "input_ids": inputs.tolist(), "cue0": cue0.tolist(), "cue1": cue1.tolist(),
                "probe_ids": probes.tolist(), "graph_diagnostics": graph_diag,
                "primary_rate_match_ok": bool(calibration["primary_rate_match_ok"]),
                "common_target_rate": calibration["common_target_rate"],
                "primary_max_relative_error": calibration["primary_max_relative_error"],
                "variants": calibration["variants"],
                "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
            }
            write_json_once(cal_path, caldata)
        calibration = {
            "primary_rate_match_ok": caldata["primary_rate_match_ok"],
            "common_target_rate": caldata["common_target_rate"],
            "variants": caldata["variants"],
        }
        for lag in lags:
            cell_path = stage_dir / f"seed_{seed:04d}_lag_{lag:03d}.json"
            existing = read_checkpoint(cell_path, protocol_hash, runner_hash)
            if existing is not None:
                continue
            row = run_cell(
                variants, calibration, cfg, inputs, cue0, cue1, probes,
                protocol_hash, runner_hash, stage, seed, lag, trials, run_rnn,
            )
            row["graph_diagnostics"] = graph_diag
            row["graph_sha256"] = graph_sha
            row["config_sha256"] = cfg_hash
            write_json_once(cell_path, row)
            print(json.dumps({
                "stage": stage, "seed": seed, "lag": lag,
                "live": {k: v["alive"] for k, v in row["results"].items()},
                "acc": {k: v["accuracy"] for k, v in row["results"].items()},
                "wall_s": round(row["cell_wall_seconds"], 3),
                "rate_match": caldata["primary_rate_match_ok"],
            }), flush=True)

    summary = aggregate_stage(stage_dir, stage, seeds, runner_hash, protocol_hash)
    summary_path = stage_dir / "summary.json"
    if not summary_path.exists():
        write_json_once(summary_path, summary)
    complete_path = stage_dir / "stage_complete.json"
    if not complete_path.exists():
        write_json_once(complete_path, {
            "stage": stage, "completed_utc": datetime.now(timezone.utc).isoformat(),
            "status": summary.get("status", "SMOKE_COMPLETE"),
            "summary_path": str(summary_path.relative_to(ROOT)),
            "protocol_sha256": protocol_hash, "runner_sha256": runner_hash,
        })
    print(json.dumps({
        "run_root": str(run_root), "stage": stage,
        "status": summary.get("status", "SMOKE_COMPLETE"),
        "summary": str(summary_path.relative_to(ROOT)),
        "primary_rate_match": summary.get("all_primary_rate_matches_passed"),
        "liveness": summary.get("all_network_liveness_passed"),
    }, indent=2), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "sizing", "confirm", "extension"), required=True)
    parser.add_argument("--run-root", type=Path)
    args = parser.parse_args(argv)
    if not PROTOCOL.is_file():
        parser.error(f"missing frozen preregistration: {PROTOCOL}")
    if args.run_root is None:
        args.run_root = make_run_root()
    run_stage(args.stage, args.run_root, H.load_cfg())


if __name__ == "__main__":
    main()
