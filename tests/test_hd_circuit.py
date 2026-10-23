import numpy as np

from flylab.nulls import block_preserving_null, degree_sequences
from flylab.slice import load_hd_circuit


def _mixed_sign_sources(src, w):
    return sum(len(np.unique(np.sign(w[(src == s) & (w != 0)]))) > 1 for s in np.unique(src))


def test_hd_circuit_is_the_documented_dataset():
    sl, neurons = load_hd_circuit()
    assert sl.n == 152 and len(sl.src) == 9160
    counts = neurons["type"].value_counts().to_dict()
    assert counts["EPG"] == 46 and counts["Delta7"] == 42
    # Delta7 are glutamatergic and must carry inhibition here (zero under the E1 policy).
    d7 = np.flatnonzero(neurons["type"].to_numpy() == "Delta7")
    out = sl.signed_weight[np.isin(sl.src, d7)]
    assert len(out) and (out < 0).all()
    assert _mixed_sign_sources(sl.src, sl.signed_weight) == 0
    epg = neurons[neurons["type"] == "EPG"]
    assert (epg["pb_glomerulus"].str.match(r"^[LR][1-8]$")).all()


def test_block_null_keeps_degrees_blocks_dale_and_moves_edges():
    sl, neurons = load_hd_circuit()
    labels = neurons["type"].to_numpy()
    A, diag = block_preserving_null(sl.src, sl.dst, sl.signed_weight, sl.n, labels,
                                    np.random.default_rng(0), n_swaps_per_edge=5)
    C = A.tocoo()
    assert diag["fraction_edges_rewired"] > 0.3
    assert _mixed_sign_sources(C.col, C.data) == 0
    assert np.allclose(np.bincount(C.col, C.data, sl.n), np.bincount(sl.src, sl.signed_weight, sl.n))
    o0, i0 = degree_sequences(sl.src, sl.dst, sl.n)
    o1, i1 = degree_sequences(C.col, C.row, sl.n)
    assert np.array_equal(o0, o1) and np.array_equal(i0, i1)
    blk = lambda s, d: sorted(zip(labels[s], labels[d], strict=True))
    assert blk(C.col, C.row) == blk(sl.src, sl.dst)


def test_block_null_on_toy_graph_never_crosses_blocks(toy_graph):
    n, src, dst, w = toy_graph
    labels = np.arange(n) % 3
    A, diag = block_preserving_null(src, dst, np.abs(w), n, labels, np.random.default_rng(1), 10)
    C = A.tocoo()
    before = sorted(zip(labels[src], labels[dst], strict=True))
    after = sorted(zip(labels[C.col], labels[C.row], strict=True))
    assert before == after and diag["swaps_accepted"] > 0
