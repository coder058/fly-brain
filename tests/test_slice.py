import numpy as np
import pytest

from flylab.graph import GRAPH_DIR
from flylab.slice import load_slice


def test_bundled_slice_is_the_documented_e1_subgraph():
    sl = load_slice()  # verifies the recorded sha256
    assert sl.n == 500
    assert len(sl.src) == 23_708  # E1 subgraph size quoted in flylab/nulls.py
    # Four autapses (self-synapses, total |w| = 15 of 225,583). The degree-preserving null
    # rewires them away because its output must be a simple graph; the effect is negligible.
    assert int((sl.src == sl.dst).sum()) == 4
    assert len(np.unique(np.stack([sl.src, sl.dst], 1), axis=0)) == len(sl.src)
    assert len(np.unique(sl.body_id)) == 500


@pytest.mark.skipif(not (GRAPH_DIR / "graph_meta.json").exists(),
                    reason="full MaleCNS graph not built (scripts/build_graph.py)")
def test_bundled_slice_equals_harness_extraction_from_full_graph():
    import e1_reservoir as H
    from flylab.dynamics import post_pre_from_pre_post
    from flylab.graph import induced_subgraph, load_graph

    g = load_graph(load_neurons=False)
    A, _ = induced_subgraph(g, H.select_nodes(g, 500))
    W_harness = post_pre_from_pre_post(A)
    assert (W_harness != load_slice().W()).nnz == 0
