"""Control graphs and the gate's decision rule."""
import numpy as np
import pytest
from scipy import sparse

import e1_reservoir as E
import positive_control as PC
from flylab.nulls import er_graph, ring_lattice
from flylab.spectral import gain_for_target_rate


def test_ring_lattice_is_a_regular_ring():
    n, nnz = 200, 1200
    W = ring_lattice(n, nnz, np.random.default_rng(0))  # (post, pre)
    out_deg = np.asarray((W != 0).sum(0)).ravel()
    assert W.diagonal().sum() == 0, "ring lattice must have no self-loops"
    assert out_deg.min() == out_deg.max() == nnz // n
    assert W.nnz == nnz
    assert (W.data > 0).all(), "positive control ring is all-excitatory by construction"


def test_er_graph_is_simple_and_exact():
    n, nnz = 200, 1200
    W = er_graph(n, nnz, np.random.default_rng(0))
    assert W.nnz == nnz
    assert W.diagonal().sum() == 0


def test_ring_and_er_are_matched_on_everything_but_topology():
    n, nnz = 200, 1200
    r = ring_lattice(n, nnz, np.random.default_rng(0))
    e = er_graph(n, nnz, np.random.default_rng(0), excitatory_only=True)
    assert r.shape == e.shape and r.nnz == e.nnz
    assert (r.data > 0).all() and (e.data > 0).all()
    assert r.data.min() >= 1.0 and r.data.max() <= 10.0
    assert e.data.min() >= 1.0 and e.data.max() <= 10.0


def test_gate_requires_both_an_effect_and_a_ci_that_excludes_zero():
    tiny = PC.verdict(PC.paired_stats([0.51] * 6, [0.50] * 6))
    assert tiny["ci_excludes_zero"] is False or tiny["separated"] is False

    noisy = PC.verdict(PC.paired_stats([0.9, 0.2, 0.9, 0.2, 0.9, 0.2], [0.5] * 6))
    assert noisy["separated"] is False, "wide CI must not count as separation"

    clean = PC.verdict(PC.paired_stats([0.80, 0.78, 0.82, 0.79, 0.81, 0.80], [0.60] * 6))
    assert clean["separated"] is True


def test_pc_b_rejects_dead_or_unmatched_seed_instead_of_scoring_claim():
    rows = [
        {"seed": 1, "ring": {"acc": 0.8, "matched": True},
         "er": {"acc": 0.6, "matched": True}},
        {"seed": 2, "ring": {"acc": None, "matched": True},
         "er": {"acc": 0.6, "matched": True}},
    ]
    result = PC.pc_b_verdict(rows)
    assert result["valid"] is False
    assert result["separated"] is False
    assert result["invalid_seeds"] == [2]
    assert result["mean_diff"] is None


def test_gain_bisection_finds_a_monotone_target():
    res = gain_for_target_rate(lambda g: 0.001 * g**2, target_rate=0.01, lo=0.05, hi=60.0)
    assert res["converged"]
    assert res["rate"] == pytest.approx(0.01, rel=0.15)


def test_gain_bisection_reports_unreachable_targets():
    assert gain_for_target_rate(lambda g: 0.0, 0.01)["converged"] is False
    assert gain_for_target_rate(lambda g: 1.0, 0.01)["converged"] is False


def test_ops_proxy_counts_nonzero_sparse_synapses_only():
    W = sparse.csr_matrix(([2.0, 0.0, -1.0], ([0, 0, 1], [0, 1, 0])), shape=(2, 2))
    assert E.effective_nonzero_nnz(W) == 2
    assert E.ops_proxy(E.effective_nonzero_nnz(W), 3, 4) == 48.0
