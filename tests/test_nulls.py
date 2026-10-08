"""The degree-preserving null must actually preserve degrees.

The original implementation permuted the destination array and rebuilt a COO matrix, so
scipy silently summed colliding duplicates: 7.93% of edges vanished and self-loops appeared.
"""
import numpy as np
import pytest
from scipy import sparse

import e1_reservoir as H
from flylab.nulls import degree_preserving_null, degree_sequences, directed_edge_swap


def test_degree_preserving_null_preserves_both_degree_sequences(toy_graph):
    n, src, dst, w = toy_graph
    out0, in0 = degree_sequences(src, dst, n)
    A, diag = degree_preserving_null(src, dst, w, n, np.random.default_rng(0))
    ns, nd = A.tocoo().col, A.tocoo().row  # A is (post, pre)
    out1, in1 = degree_sequences(ns, nd, n)
    assert np.array_equal(out0, out1)
    assert np.array_equal(in0, in1)
    assert diag["out_degree_preserved"] and diag["in_degree_preserved"]


def test_degree_preserving_null_loses_no_edges_and_makes_no_self_loops(toy_graph):
    n, src, dst, w = toy_graph
    A, diag = degree_preserving_null(src, dst, w, n, np.random.default_rng(1))
    assert A.nnz == len(src)
    assert diag["n_edges_out"] == diag["n_edges_in"] == len(src)
    assert diag["self_loops"] == 0
    assert diag["duplicate_edges"] == 0
    assert A.diagonal().sum() == 0


def test_degree_preserving_null_actually_rewires(toy_graph):
    n, src, dst, w = toy_graph
    A, diag = degree_preserving_null(src, dst, w, n, np.random.default_rng(2))
    assert diag["fraction_edges_rewired"] > 0.5


def test_degree_preserving_null_is_deterministic(toy_graph):
    n, src, dst, w = toy_graph
    a, _ = degree_preserving_null(src, dst, w, n, np.random.default_rng(3))
    b, _ = degree_preserving_null(src, dst, w, n, np.random.default_rng(3))
    assert (a != b).nnz == 0


def test_degree_preserving_null_preserves_the_weight_multiset(toy_graph):
    n, src, dst, w = toy_graph
    A, _ = degree_preserving_null(src, dst, w, n, np.random.default_rng(4))
    assert np.allclose(np.sort(A.data), np.sort(w.astype(np.float32)))


def test_old_shuffle_is_demonstrably_not_degree_preserving(toy_graph):
    """Regression witness for the bug, so it cannot come back unnoticed."""
    n, src, dst, w = toy_graph
    out0, in0 = degree_sequences(src, dst, n)
    W = H.degree_shuffle_v0_broken(src, dst, w, n, np.random.default_rng(0))
    coo = W.tocoo()
    out1, in1 = degree_sequences(coo.col, coo.row, n)
    assert W.nnz < len(src), "old shuffle lost edges to duplicate collisions"
    assert not (np.array_equal(out0, out1) and np.array_equal(in0, in1))


def test_harness_degree_shuffle_now_delegates_to_the_correct_null(toy_graph):
    n, src, dst, w = toy_graph
    W, diag = H.degree_shuffle(src, dst, w, n, np.random.default_rng(0), return_diag=True)
    assert W.nnz == len(src)
    assert diag["self_loops"] == 0 and diag["duplicate_edges"] == 0


def test_swap_rejects_moves_that_would_create_self_loops_or_duplicates():
    n = 6
    src = np.array([0, 1, 2, 3])
    dst = np.array([1, 2, 3, 4])
    ns, nd, perm = directed_edge_swap(src, dst, n, np.random.default_rng(0), 50)
    assert np.array_equal(np.sort(ns), np.sort(src))
    assert (ns != nd).all()
    assert len(np.unique(np.stack([ns, nd], 1), axis=0)) == len(ns)


def test_weight_permutation_keeps_topology_and_weight_multiset(toy_graph):
    from flylab.nulls import weight_permutation_null
    n, src, dst, w = toy_graph
    out0, in0 = degree_sequences(src, dst, n)
    A, diag = weight_permutation_null(src, dst, w, n, np.random.default_rng(0))
    ns, nd = A.tocoo().col, A.tocoo().row
    out1, in1 = degree_sequences(ns, nd, n)
    assert np.array_equal(out0, out1) and np.array_equal(in0, in1)
    assert diag["topology_preserved"]
    assert np.allclose(np.sort(A.data), np.sort(w.astype(np.float32)))
    assert A.nnz == len(src)


def test_weight_permutation_is_deterministic(toy_graph):
    from flylab.nulls import weight_permutation_null
    n, src, dst, w = toy_graph
    a, _ = weight_permutation_null(src, dst, w, n, np.random.default_rng(7))
    b, _ = weight_permutation_null(src, dst, w, n, np.random.default_rng(7))
    assert (a != b).nnz == 0


def test_remove_topk_hubs_drops_incident_edges(toy_graph):
    from flylab.nulls import remove_topk_hubs
    n, src, dst, w = toy_graph
    k = 2
    out_deg = np.bincount(src, minlength=n)
    hubs = set(np.argsort(out_deg)[-k:].tolist())
    A, diag = remove_topk_hubs(src, dst, w, n, k)
    assert diag["k"] == k
    assert A.nnz == diag["n_edges_out"]
    assert diag["edges_removed"] + A.nnz == len(src)
    coo = A.tocoo()
    remaining = set(coo.col.tolist()) | set(coo.row.tolist())
    assert hubs.isdisjoint(remaining) or A.nnz == 0 or True
    # remaining endpoints must not include hubs
    if A.nnz:
        assert not set(coo.col.tolist()) & hubs
        assert not set(coo.row.tolist()) & hubs


def _mixed_sign_sources(src, w):
    return sum(len(np.unique(np.sign(w[(src == s) & (w != 0)]))) > 1 for s in np.unique(src))


def test_dale_null_keeps_presynaptic_sign_and_out_strength():
    from flylab.nulls import degree_preserving_null
    from flylab.slice import load_slice

    sl = load_slice()
    for follow, dale_kept in (("pre", True), ("post", False)):
        A, diag = degree_preserving_null(sl.src, sl.dst, sl.signed_weight, sl.n,
                                         np.random.default_rng([90_000, 0]), 5,
                                         weights_follow=follow)
        C = A.tocoo()
        mixed = _mixed_sign_sources(C.col, C.data)
        out_kept = np.allclose(np.bincount(C.col, C.data, sl.n),
                               np.bincount(sl.src, sl.signed_weight, sl.n))
        in_kept = np.allclose(np.bincount(C.row, C.data, sl.n),
                              np.bincount(sl.dst, sl.signed_weight, sl.n))
        assert diag["weights_follow"] == follow
        if dale_kept:
            assert mixed == 0 and out_kept
        else:
            # legacy convention, kept bit-for-bit so historical results reproduce
            assert mixed > 400 and in_kept and not out_kept
    assert _mixed_sign_sources(sl.src, sl.signed_weight) == 0
