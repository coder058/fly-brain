#!/usr/bin/env python3
"""ROUTING-001: two-stream routing with preregistered matched controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import numpy as np
import pyarrow.feather as feather
from scipy import sparse
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "harness"))

from flylab.dynamics import LIFParams, LIFState, post_pre_from_pre_post, step_lif
from flylab.graph import induced_subgraph, load_graph
from flylab.nulls import degree_preserving_null
from flylab.spectral import arm_spectrum, gain_for_target_rate, syn_scale_for_gain
import e1_reservoir as E1


# SOURCE: existing E1 CPU-first subgraph selection in experiments/harness/e1_reservoir.py.
N_SUBGRAPH = 500
# GUESS: locked task width for a two-stream CPU smoke/full run; not calibrated from results.
N_INPUTS_PER_STREAM = 16
# GUESS: locked readout width for a two-stream CPU smoke/full run; not calibrated from results.
N_PROBES_PER_STREAM = 32
# GUESS: locked trial count for power without changing the protocol after metrics.
N_TRIALS_PER_PATTERN = 20
# GUESS: short-horizon routing window; not a memory delay or biological timescale.
N_STEPS = 32
# GUESS: pulse width sufficient to drive the locked LIF task; not fitted to graph results.
PULSE_STEPS = 4
# SOURCE: existing E1 config I_amp.
I_AMP = 6.0
# GUESS: locked noise for non-privileged input perturbation; not a finding.
INPUT_NOISE = 0.20
# SOURCE: existing E1 LIF configuration.
DT = 1.0
TAU_M = 6.0
V_REST = 0.0
V_RESET = 0.0
V_TH = 1.0
R = 1.0
# GUESS: four temporal bins provide a short readout without using input neurons.
N_BINS = 4
# SOURCE: validated instrument target rate in EXP-INST-001.
TARGET_RATE = 0.002
# SOURCE: existing gain matching bounds used by the harness.
GAIN_LO = 0.05
GAIN_HI = 80.0
GAIN_REL_TOL = 0.15
GAIN_MAX_ITER = 24
# SOURCE: existing E1 train split convention.
TRAIN_FRACTION = 0.70
# SOURCE: campaign requirement.
SEEDS = tuple(range(12))
# SOURCE: preregistered protocol block null setting.
BLOCK_SWAPS_PER_EDGE = 8
# SOURCE: existing degree-preserving null engine setting.
DEGREE_SWAPS_PER_EDGE = 20
# SOURCE: preregistered liveness minimum for the full run.
MIN_UNIQUE_ROWS = 10
# SOURCE: smoke-only diagnostic rule; smoke is explicitly not evidence.
SMOKE_MIN_UNIQUE_ROWS = 2
# SOURCE: existing instrument minimum-effect gate.
MIN_ROUTING_MARGIN = 0.10
# GUESS: positive-control edge weight, locked before the run.
POS_DIRECT_WEIGHT = 2.0
# GUESS: positive-control background weight, locked before the run.
POS_BACKGROUND_WEIGHT = 0.10
# SOURCE: independent RNG stream labels, fixed before metrics.
TASK_STREAM = 70101
CAL_STREAM = 70102
ARM_STREAM = 70103
POS_STREAM = 70104
# SOURCE: smoke definition in ROUTING-001-PROTOCOL.md.
SMOKE_TRIALS_PER_PATTERN = 2
SMOKE_SEEDS = (0,)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_rev() -> str:
    try:
        p = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return p.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json_once(path: Path, obj: dict) -> None:
    if path.exists():
        raise RuntimeError("refusing to overwrite " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, default=_json_default) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def load_superclasses() -> np.ndarray:
    table = feather.read_table(
        ROOT / "data" / "derived" / "graph" / "neurons.feather",
        columns=["neuron_id", "superclass"],
    ).to_pydict()
    node_ids = np.asarray(table["neuron_id"], dtype=np.int64)
    if not np.array_equal(node_ids, np.arange(len(node_ids), dtype=np.int64)):
        raise ValueError("neurons.feather is not in node-id order")
    return np.asarray(
        [str(x) if x not in (None, "") else "UNANNOTATED"
         for x in table["superclass"]],
        dtype=str,
    )


def choose_nodes(g) -> tuple[np.ndarray, np.ndarray]:
    # SOURCE: exact existing E1 select_nodes rule, preserving the fixed CPU subgraph.
    degree = np.diff(g.csr.indptr).astype(np.int64, copy=False)
    nodes = np.sort(np.argsort(degree)[-N_SUBGRAPH:])
    return nodes, degree


def choose_streams(nodes: np.ndarray, degree: np.ndarray, labels: np.ndarray) -> dict:
    local_labels = labels[nodes]
    local_degree = degree[nodes]
    names, counts = np.unique(local_labels, return_counts=True)
    order = sorted(range(len(names)), key=lambda i: (-int(counts[i]), str(names[i])))
    if len(order) < 2:
        raise RuntimeError("fewer than two superclass groups in fixed subgraph")
    selected = [str(names[i]) for i in order[:2]]
    streams = {}
    for channel, label in zip(("A", "B"), selected):
        members = np.flatnonzero(local_labels == label).astype(np.int64)
        if len(members) < N_INPUTS_PER_STREAM + N_PROBES_PER_STREAM:
            raise RuntimeError("selected superclass lacks locked input/probe capacity")
        # SOURCE: repaired fixed-ID partition locked after smoke instrument diagnosis.
        # It avoids degree-selected probes that were silent in the block null.
        inputs = members[:N_INPUTS_PER_STREAM]
        probes = members[N_INPUTS_PER_STREAM:N_INPUTS_PER_STREAM + N_PROBES_PER_STREAM]
        streams[channel] = {
            "label": label,
            "members": members,
            "global_members": nodes[members].astype(np.int64),
            "inputs": inputs.astype(np.int64),
            "global_inputs": nodes[inputs].astype(np.int64),
            "probes": probes.astype(np.int64),
            "global_probes": nodes[probes].astype(np.int64),
        }
    streams["selected_labels"] = selected
    streams["input_ids"] = np.concatenate([streams["A"]["inputs"], streams["B"]["inputs"]])
    streams["probe_ids"] = np.concatenate([streams["A"]["probes"], streams["B"]["probes"]])
    return streams


def make_block_null(src, dst, weights, labels, rng: np.random.Generator) -> tuple[sparse.csr_matrix, dict]:
    """Swap destinations only inside source/destination label blocks."""
    src = np.asarray(src, dtype=np.int64).copy()
    dst = np.asarray(dst, dtype=np.int64).copy()
    original_dst = dst.copy()
    weights = np.asarray(weights, dtype=np.float32).copy()
    n = int(len(labels))
    present = set(zip(src.tolist(), dst.tolist()))
    blocks = defaultdict(list)
    for i, (a, b) in enumerate(zip(src, dst)):
        blocks[(str(labels[a]), str(labels[b]))].append(i)
    accepted_total = 0
    attempts_total = 0
    block_reports = {}
    for block, raw_indices in sorted(blocks.items()):
        indices = np.asarray(raw_indices, dtype=np.int64)
        target = int(len(indices) * BLOCK_SWAPS_PER_EDGE)
        accepted = 0
        attempts = 0
        max_attempts = max(20, target * 10)
        while accepted < target and attempts < max_attempts and len(indices) > 1:
            attempts += 1
            i, j = rng.choice(indices, size=2, replace=False)
            a, b = int(src[i]), int(dst[i])
            c, d = int(src[j]), int(dst[j])
            if a == d or c == b:
                continue
            if (a, d) in present or (c, b) in present:
                continue
            present.discard((a, b))
            present.discard((c, d))
            present.add((a, d))
            present.add((c, b))
            dst[i], dst[j] = d, b
            accepted += 1
        accepted_total += accepted
        attempts_total += attempts
        block_reports["|".join(block)] = {
            "edges": int(len(indices)),
            "accepted_swaps": int(accepted),
            "attempts": int(attempts),
            "target_swaps": int(target),
        }
    A = sparse.csr_matrix((weights, (dst, src)), shape=(n, n))
    original_blocks = [(str(labels[a]), str(labels[b])) for a, b in zip(src, original_dst)]
    new_blocks = [(str(labels[a]), str(labels[b])) for a, b in zip(src, dst)]
    diag = {
        "n_edges_in": int(len(src)),
        "n_edges_out": int(A.nnz),
        "self_loops": int(np.sum(src == dst)),
        "duplicate_edges": int(len(src) - len(set(zip(src.tolist(), dst.tolist())))),
        "block_counts_preserved": bool(sorted(original_blocks) == sorted(new_blocks)),
        "weight_multiset_preserved": True,
        "accepted_swaps": int(accepted_total),
        "attempts": int(attempts_total),
        "fraction_edges_rewired": float(np.mean(dst != original_dst)) if len(dst) else 0.0,
        "blocks": block_reports,
    }
    if diag["n_edges_out"] != len(src) or diag["duplicate_edges"] or not diag["block_counts_preserved"]:
        raise RuntimeError("invalid block-preserving null: " + json.dumps(diag))
    return A, diag


def build_graph_arms(g, nodes, labels, seed: int) -> tuple[dict, dict]:
    A, mapped = induced_subgraph(g, nodes)
    if not np.array_equal(mapped, nodes):
        raise RuntimeError("induced-subgraph mapping changed")
    n = len(nodes)
    W_conn = post_pre_from_pre_post(A)
    mask = np.isin(g.src, nodes) & np.isin(g.dst, nodes)
    remap = -np.ones(g.n, dtype=np.int64)
    remap[nodes] = np.arange(n, dtype=np.int64)
    src = remap[g.src[mask]]
    dst = remap[g.dst[mask]]
    weights = g.signed_weight[mask].astype(np.float32)
    local_labels = labels[nodes]
    rng = np.random.default_rng([ARM_STREAM, int(seed)])
    W_degree, degree_diag = degree_preserving_null(
        src, dst, weights, n, rng, n_swaps_per_edge=DEGREE_SWAPS_PER_EDGE
    )
    W_block, block_diag = make_block_null(src, dst, weights, local_labels, rng)
    return {
        "connectome_signed": W_conn,
        "degree_preserving": W_degree,
        "block_preserving": W_block,
    }, {
        "connectome_signed": {"nnz": int(W_conn.nnz)},
        "degree_preserving": degree_diag,
        "block_preserving": block_diag,
        "source_edges": int(len(src)),
        "source_self_loops": int(np.sum(src == dst)),
    }


def positive_graph(n: int, streams: dict, nnz_hint: int, seed: int) -> sparse.csr_matrix:
    """Known routing graph; direct same-channel edges are always included."""
    direct = []
    for key in ("A", "B"):
        for src in streams[key]["inputs"]:
            for dst in streams[key]["probes"]:
                direct.append((int(src), int(dst)))
    direct = list(dict.fromkeys(direct))
    all_block = []
    for key in ("A", "B"):
        members = streams[key]["members"]
        for src in members:
            for dst in members:
                if int(src) != int(dst):
                    all_block.append((int(src), int(dst)))
    edge_set = set(direct)
    extras = [e for e in all_block if e not in edge_set]
    rng = np.random.default_rng([POS_STREAM, int(seed)])
    target = max(len(edge_set), min(int(nnz_hint), len(edge_set) + len(extras)))
    if target > len(edge_set):
        chosen = rng.choice(len(extras), size=target - len(edge_set), replace=False)
        edge_set.update(extras[int(i)] for i in chosen)
    ordered = direct + sorted(edge_set.difference(direct))
    src = np.asarray([e[0] for e in ordered], dtype=np.int64)
    dst = np.asarray([e[1] for e in ordered], dtype=np.int64)
    w = np.full(len(ordered), POS_BACKGROUND_WEIGHT, dtype=np.float32)
    w[:len(direct)] = POS_DIRECT_WEIGHT
    return sparse.csr_matrix((w, (dst, src)), shape=(n, n))


def make_trials(n: int, streams: dict, seed: int, trials_per_pattern: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    patterns = np.repeat(np.asarray([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=np.int64),
                         trials_per_pattern, axis=0)
    currents = np.zeros((len(patterns), N_STEPS, n), dtype=np.float32)
    input_ids = streams["input_ids"]
    for trial, (a, b) in enumerate(patterns):
        rng = np.random.default_rng([TASK_STREAM, int(seed), int(trial)])
        currents[trial, :, input_ids] = rng.normal(
            0.0, INPUT_NOISE, size=(N_STEPS, len(input_ids))
        ).astype(np.float32)
        if int(a):
            currents[trial, :PULSE_STEPS, streams["A"]["inputs"]] += I_AMP
        if int(b):
            currents[trial, :PULSE_STEPS, streams["B"]["inputs"]] += I_AMP
    train = []
    test = []
    for start in range(0, len(patterns), trials_per_pattern):
        cut = int(TRAIN_FRACTION * trials_per_pattern)
        train.extend(range(start, start + cut))
        test.extend(range(start + cut, start + trials_per_pattern))
    return currents, patterns, np.asarray(train, dtype=np.int64), np.asarray(test, dtype=np.int64)


def make_calibration(n: int, streams: dict, seed: int) -> np.ndarray:
    # SOURCE: eight separate calibration trials and the same input encoding.
    currents = np.zeros((8, N_STEPS, n), dtype=np.float32)
    ids = streams["input_ids"]
    for trial in range(len(currents)):
        rng = np.random.default_rng([CAL_STREAM, int(seed), int(trial)])
        currents[trial, :, ids] = rng.normal(
            0.0, INPUT_NOISE, size=(N_STEPS, len(ids))
        ).astype(np.float32)
        currents[trial, :PULSE_STEPS, ids] += I_AMP
    return currents


def lif_for_gain(W: sparse.csr_matrix, spec: dict, gain: float) -> LIFParams:
    # SOURCE: existing MEM-002/MEM-003 rate-matching convention; robust to signed inhibition.
    rho = float(spec["rho_abs"])
    if rho <= 0.0:
        raise ValueError("non-positive signed spectral radius")
    return LIFParams(
        dt=DT, tau_m=TAU_M, v_rest=V_REST, v_reset=V_RESET, v_th=V_TH,
        r=R, syn_scale=syn_scale_for_gain(rho, gain, TAU_M, DT, R),
    )


def simulate_features(W: sparse.csr_matrix, currents: np.ndarray, lif: LIFParams,
                      seed: int, input_ids: np.ndarray, probe_ids: np.ndarray) -> tuple[np.ndarray, dict]:
    """Use membrane-state features so signed inhibition is observable, not silently discarded."""
    n = W.shape[0]
    input_ids = np.asarray(input_ids, dtype=np.int64)
    probe_ids = np.asarray(probe_ids, dtype=np.int64)
    if np.intersect1d(input_ids, probe_ids).size:
        raise ValueError("input/probe overlap")
    probe_count = len(probe_ids)
    pool = np.ones(n, dtype=bool)
    pool[input_ids] = False
    X = np.zeros((len(currents), N_BINS * probe_count), dtype=np.float32)
    pool_per_trial = np.zeros(len(currents), dtype=np.float64)
    probe_a_spikes = np.zeros(len(currents), dtype=np.float64)
    probe_b_spikes = np.zeros(len(currents), dtype=np.float64)
    probe_a_state_std = np.zeros(len(currents), dtype=np.float64)
    probe_b_state_std = np.zeros(len(currents), dtype=np.float64)
    split_probe = probe_count // 2
    edges = np.linspace(0, N_STEPS, N_BINS + 1, dtype=np.int64)
    for trial, drive in enumerate(currents):
        rng = np.random.default_rng([ARM_STREAM, int(seed), int(trial)])
        state = LIFState(
            v=rng.normal(V_REST, 0.05, size=n).astype(np.float32),
            spikes=np.zeros(n, dtype=np.float32),
        )
        state_raster = np.zeros((N_STEPS, probe_count), dtype=np.float32)
        spike_raster = np.zeros((N_STEPS, probe_count), dtype=np.float32)
        for step, current in enumerate(drive):
            state = step_lif(W, state, current, lif)
            pool_per_trial[trial] += float(state.spikes[pool].sum())
            state_raster[step] = state.v[probe_ids]
            spike_raster[step] = state.spikes[probe_ids]
        probe_a_spikes[trial] = float(spike_raster[:, :split_probe].sum())
        probe_b_spikes[trial] = float(spike_raster[:, split_probe:].sum())
        probe_a_state_std[trial] = float(state_raster[:, :split_probe].std())
        probe_b_state_std[trial] = float(state_raster[:, split_probe:].std())
        for b in range(N_BINS):
            X[trial, b * probe_count:(b + 1) * probe_count] = state_raster[
                edges[b]:edges[b + 1]
            ].mean(axis=0)
    return X, {
        "pool_spikes": pool_per_trial,
        "probe_a_spikes": probe_a_spikes,
        "probe_b_spikes": probe_b_spikes,
        "probe_a_state_std": probe_a_state_std,
        "probe_b_state_std": probe_b_state_std,
    }


def liveness(X: np.ndarray, stats: dict, train: np.ndarray, test: np.ndarray,
             min_unique_rows: int = MIN_UNIQUE_ROWS) -> dict:
    reports = {}
    for name, idx in (("train", train), ("test", test)):
        block = X[idx]
        problems = []
        if float(stats["pool_spikes"][idx].sum()) <= 0.0:
            problems.append("non_input_pool_silent")
        if float(stats["probe_a_state_std"][idx].max(initial=0.0)) <= np.finfo(np.float32).eps:
            problems.append("A_probe_state_silent")
        if float(stats["probe_b_state_std"][idx].max(initial=0.0)) <= np.finfo(np.float32).eps:
            problems.append("B_probe_state_silent")
        if float(block.std()) <= 1e-6:
            problems.append("feature_std_too_small")
        unique = int(np.unique(np.round(block, 6), axis=0).shape[0])
        if unique < int(min_unique_rows):
            problems.append("unique_feature_rows_below_gate")
        reports[name] = {
            "alive": not problems,
            "problems": problems,
            "pool_spikes": float(stats["pool_spikes"][idx].sum()),
            "probe_a_spikes": float(stats["probe_a_spikes"][idx].sum()),
            "probe_b_spikes": float(stats["probe_b_spikes"][idx].sum()),
            "probe_a_state_std_max": float(stats["probe_a_state_std"][idx].max(initial=0.0)),
            "probe_b_state_std_max": float(stats["probe_b_state_std"][idx].max(initial=0.0)),
            "feature_std": float(block.std()),
            "unique_feature_rows": unique,
        }
    return {
        "train": reports["train"],
        "test": reports["test"],
        "alive": bool(reports["train"]["alive"] and reports["test"]["alive"]),
    }


def split_channels(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    width = N_PROBES_PER_STREAM
    chunks_a = []
    chunks_b = []
    for b in range(N_BINS):
        start = b * 2 * width
        chunks_a.append(X[:, start:start + width])
        chunks_b.append(X[:, start + width:start + 2 * width])
    return np.hstack(chunks_a), np.hstack(chunks_b)


def binary_accuracy(X: np.ndarray, y: np.ndarray, train: np.ndarray,
                    test: np.ndarray, seed: int) -> float:
    r = E1.ridge_sweep(
        X[train], y[train], X[test], y[test], n_classes=2, seed=int(seed)
    )
    return float(r["acc"])


def routing_metrics(X: np.ndarray, patterns: np.ndarray,
                    train: np.ndarray, test: np.ndarray, seed: int) -> dict:
    XA, XB = split_channels(X)
    within_a = binary_accuracy(XA, patterns[:, 0], train, test, seed + 100)
    within_b = binary_accuracy(XB, patterns[:, 1], train, test, seed + 101)
    cross_a = binary_accuracy(XB, patterns[:, 0], train, test, seed + 102)
    cross_b = binary_accuracy(XA, patterns[:, 1], train, test, seed + 103)
    within = 0.5 * (within_a + within_b)
    cross = 0.5 * (cross_a + cross_b)
    return {
        "within_A_from_A": within_a,
        "within_B_from_B": within_b,
        "cross_A_from_B": cross_a,
        "cross_B_from_A": cross_b,
        "within_mean": float(within),
        "cross_mean": float(cross),
        "routing_margin": float(within - cross),
        "chance_binary": 0.5,
    }


def calibrate(W: sparse.csr_matrix, streams: dict, seed: int) -> dict:
    spec = arm_spectrum(W)
    if float(spec["rho_signed"]) <= 0.0:
        return {"accepted": False, "reason": "non_positive_signed_spectral_radius", "spectrum": spec}
    currents = make_calibration(W.shape[0], streams, seed)
    inputs = streams["input_ids"]
    pool_size = W.shape[0] - len(inputs)

    def rate_fn(gain: float) -> float:
        lif = lif_for_gain(W, spec, gain)
        _, stats = simulate_features(W, currents, lif, seed, inputs, streams["probe_ids"])
        return float(stats["pool_spikes"].sum() / (len(currents) * N_STEPS * pool_size))

    result = gain_for_target_rate(
        rate_fn, TARGET_RATE, lo=GAIN_LO, hi=GAIN_HI,
        tol=GAIN_REL_TOL, max_iter=GAIN_MAX_ITER
    )
    rate = float(result["rate"])
    accepted = bool(np.isfinite(rate) and abs(rate - TARGET_RATE) <= GAIN_REL_TOL * TARGET_RATE)
    result.update({
        "accepted": accepted,
        "target_rate": TARGET_RATE,
        "relative_tolerance": GAIN_REL_TOL,
        "pool_size": int(pool_size),
        "spectrum": spec,
        "reason": result.get("reason") if not accepted else "rate_matched",
    })
    return result


def run_arm(W: sparse.csr_matrix, arm: str, streams: dict, seed: int,
            trials_per_pattern: int, do_metrics: bool = True,
            smoke: bool = False) -> dict:
    cal = calibrate(W, streams, seed)
    row = {"arm": arm, "seed": int(seed), "calibration": cal}
    if not cal.get("accepted", False):
        row.update({"status": "MISSING", "reason": "rate_calibration_not_accepted"})
        return row
    currents, patterns, train, test = make_trials(
        W.shape[0], streams, seed, trials_per_pattern
    )
    lif = lif_for_gain(W, cal["spectrum"], float(cal["gain"]))
    X, stats = simulate_features(W, currents, lif, seed, streams["input_ids"], streams["probe_ids"])
    live = liveness(
        X, stats, train, test,
        min_unique_rows=(SMOKE_MIN_UNIQUE_ROWS if smoke else MIN_UNIQUE_ROWS),
    )
    row.update({
        "status": "MEASURED" if live["alive"] else "MISSING",
        "liveness": live,
        "n_trials": int(len(currents)),
        "train_trials": int(len(train)),
        "test_trials": int(len(test)),
        "feature_shape": list(X.shape),
    })
    if live["alive"] and do_metrics:
        row["metrics"] = routing_metrics(X, patterns, train, test, seed)
    elif not live["alive"]:
        row["reason"] = "liveness_gate_failed"
    return row


def run_seed(g, nodes, labels, streams, degree, seed: int,
             trials_per_pattern: int, outdir: Path, smoke: bool) -> dict:
    started = time.perf_counter()
    arms, diagnostics = build_graph_arms(g, nodes, labels, seed)
    nnz_hint = diagnostics["source_edges"]
    W_pos = positive_graph(len(nodes), streams, nnz_hint, seed)
    pos = run_arm(
        W_pos, "positive_control", streams, seed, trials_per_pattern,
        do_metrics=True, smoke=smoke,
    )
    pos_live = pos.get("status") == "MEASURED"
    pos_margin = pos.get("metrics", {}).get("routing_margin")
    pos_pass = bool(pos_live and (smoke or (
        pos_margin is not None and pos_margin >= MIN_ROUTING_MARGIN
    )))
    result = {
        "seed": int(seed),
        "started_utc": utc_now(),
        "selected_labels": streams["selected_labels"],
        "selected_node_count": int(len(nodes)),
        "source_edge_count": int(nnz_hint),
        "arm_diagnostics": diagnostics,
        "positive_control": pos,
        "positive_control_pass": pos_pass,
        "arms": {},
    }
    if not pos_pass:
        result["status"] = "INVALIDATED" if not smoke else "SMOKE_POSITIVE_LIVENESS_FAILED"
        result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        write_json_once(outdir / ("seed-%02d.json" % seed), result)
        return result
    for name, W in arms.items():
        result["arms"][name] = run_arm(
            W, name, streams, seed, trials_per_pattern,
            do_metrics=True, smoke=smoke
        )
    result["status"] = "SMOKE_MEASURED_NOT_EVIDENCE" if smoke else "MEASURED"
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    write_json_once(outdir / ("seed-%02d.json" % seed), result)
    return result


def aggregate(results: list[dict], smoke: bool) -> dict:
    if smoke:
        return {
            "classification": "SMOKE_NOT_EVIDENCE",
            "seeds_completed": len(results),
            "positive_control_live": [bool(r.get("positive_control_pass")) for r in results],
        }
    positive_ok = len(results) == len(SEEDS) and all(
        bool(r.get("positive_control_pass")) for r in results
    )
    rows = {name: [] for name in ("connectome_signed", "degree_preserving", "block_preserving")}
    for r in results:
        for name in rows:
            row = r.get("arms", {}).get(name)
            if row and row.get("status") == "MEASURED" and "metrics" in row:
                rows[name].append(row)
    summary = {
        "positive_control_all_pass": positive_ok,
        "arms": {},
        "paired_primary": {},
    }
    for name, items in rows.items():
        vals = np.asarray([x["metrics"]["routing_margin"] for x in items], dtype=np.float64)
        summary["arms"][name] = {
            "n_measured": int(len(vals)),
            "n_planned": int(len(SEEDS)),
            "mean_routing_margin": float(vals.mean()) if len(vals) else None,
            "sd_routing_margin": float(vals.std(ddof=1)) if len(vals) > 1 else None,
            "missing_seeds": [int(s) for s in SEEDS
                             if s not in {int(x["seed"]) for x in items}],
        }
    conn = {int(x["seed"]): float(x["metrics"]["routing_margin"])
            for x in rows["connectome_signed"]}
    block = {int(x["seed"]): float(x["metrics"]["routing_margin"])
             for x in rows["block_preserving"]}
    common = sorted(set(conn).intersection(block))
    diffs = np.asarray([conn[s] - block[s] for s in common], dtype=np.float64)
    if len(diffs) > 1:
        mean = float(diffs.mean())
        sd = float(diffs.std(ddof=1))
        crit = float(student_t.ppf(0.975, len(diffs) - 1))
        half = crit * sd / np.sqrt(len(diffs))
        ci = [mean - half, mean + half]
    elif len(diffs) == 1:
        mean = float(diffs[0])
        ci = [None, None]
    else:
        mean = None
        ci = [None, None]
    summary["paired_primary"] = {
        "seeds_common": [int(x) for x in common],
        "n": int(len(diffs)),
        "connectome_minus_block_differences": diffs,
        "mean_difference": mean,
        "ci95_paired_t": ci,
    }
    all_primary_alive = len(common) == len(SEEDS)
    conn_mean = summary["arms"]["connectome_signed"]["mean_routing_margin"]
    ci_low = ci[0]
    gate = bool(
        positive_ok and all_primary_alive and mean is not None and mean > 0.0
        and ci_low is not None and ci_low > 0.0
        and conn_mean is not None and conn_mean >= MIN_ROUTING_MARGIN
    )
    if not positive_ok:
        classification = "INVALIDATED"
    elif not all_primary_alive:
        classification = "INCONCLUSIVE"
    elif gate:
        classification = "SUPPORTED"
    else:
        classification = "NOT_SUPPORTED"
    summary["classification"] = classification
    summary["gate"] = {
        "positive_control": positive_ok,
        "all_primary_pairs_alive": all_primary_alive,
        "paired_ci_excludes_zero": bool(ci_low is not None and ci_low > 0.0),
        "connectome_margin_at_least_minimum": bool(
            conn_mean is not None and conn_mean >= MIN_ROUTING_MARGIN
        ),
        "minimum_margin": MIN_ROUTING_MARGIN,
        "claim_scope": "routing task only; not biological function, novelty, or ML transfer",
    }
    return summary


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    started = time.perf_counter()
    smoke = bool(args.smoke)
    trials = SMOKE_TRIALS_PER_PATTERN if smoke else N_TRIALS_PER_PATTERN
    seeds = SMOKE_SEEDS if smoke else SEEDS
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root_out = ROOT / "research" / "results" / "ROUTING-001"
    outdir = root_out / (("SMOKE_" if smoke else "FULL_") + stamp + "_" + git_rev()[:12])
    suffix = 1
    while outdir.exists():
        outdir = root_out / (("SMOKE_" if smoke else "FULL_") + stamp + "_" + git_rev()[:12] + "_" + str(suffix))
        suffix += 1
    outdir.mkdir(parents=True)
    protocol = ROOT / "research" / "ROUTING-001-PROTOCOL.md"
    g = load_graph(load_neurons=False)
    labels = load_superclasses()
    nodes, degree = choose_nodes(g)
    streams = choose_streams(nodes, degree, labels)
    meta = {
        "experiment": "ROUTING-001",
        "mode": "smoke" if smoke else "full",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "git_tip": git_rev(),
        "protocol_sha256": sha256_file(protocol),
        "graph_meta_sha256": sha256_file(ROOT / "data" / "derived" / "graph" / "graph_meta.json"),
        "neurons_sha256": sha256_file(ROOT / "data" / "derived" / "graph" / "neurons.feather"),
        "python": sys.version,
        "platform": platform.platform(),
        "trials_per_pattern": trials,
        "seeds_planned": [int(s) for s in seeds],
        "selected_labels": streams["selected_labels"],
        "selected_nodes": nodes,
        "selected_streams": streams,
        "n_graph_neurons": int(g.n),
        "n_graph_edges": int(g.nnz),
        "output_dir": str(outdir),
        "raw_and_derived_graph_untouched": True,
    }
    write_json_once(outdir / "metadata.json", meta)
    print(json.dumps({
        "mode": meta["mode"], "outdir": str(outdir),
        "selected_labels": streams["selected_labels"],
        "n_graph_edges": int(g.nnz), "seeds": [int(s) for s in seeds],
    }, sort_keys=True), flush=True)
    results = []
    for seed in seeds:
        print("seed", int(seed), flush=True)
        results.append(run_seed(g, nodes, labels, streams, degree, int(seed),
                                trials, outdir, smoke))
        if not smoke and results[-1].get("status") == "INVALIDATED":
            print("positive control failed; stopping graph-arm execution", flush=True)
            break
    final = {
        "experiment": "ROUTING-001",
        "mode": "smoke" if smoke else "full",
        "status": "COMPLETE" if (smoke or len(results) == len(seeds)) else "INVALIDATED",
        "git_tip": git_rev(),
        "started_utc": meta["started_utc"],
        "finished_utc": utc_now(),
        "results_dir": str(outdir),
        "seeds_completed": [int(r["seed"]) for r in results],
        "aggregate": aggregate(results, smoke),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    write_json_once(outdir / "summary.json", final)
    print(json.dumps(final["aggregate"], indent=2, sort_keys=True, default=_json_default), flush=True)
    print("WROTE", outdir / "summary.json", flush=True)


if __name__ == "__main__":
    main()
