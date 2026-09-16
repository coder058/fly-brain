"""Single accuracy-blind static input-map repair for the post-INST MEM cycle."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exp_mem_001_confirm as impl


def repaired_make_input_map(n, protocol_hash, task_seed):
    """Select sensory inputs from static positive outgoing routing only."""
    if n != impl.N_NODES:
        raise ValueError(f"mapping repair is registered only for n={impl.N_NODES}")
    graph = impl.load_graph(load_neurons=False)
    nodes = impl.H.select_nodes(graph, n)
    A, _ = impl.induced_subgraph(graph, nodes)
    scores = [int((A.getrow(j).data > 0).sum()) for j in range(n)]
    ranked = sorted(range(n), key=lambda j: (-scores[j], j))
    selected = ranked[:impl.N_INPUTS]
    inputs = np.sort(np.asarray(selected, dtype=np.int64))
    cue0 = np.asarray(selected[::2], dtype=np.int64)
    cue1 = np.asarray(selected[1::2], dtype=np.int64)
    probe_seed = impl.derive_seed(protocol_hash, "probe-map", "mapping-repair") % (2**32)
    probes, _ = impl.H.probe_set(n, inputs, impl.N_PROBES, int(probe_seed))
    if np.intersect1d(inputs, probes).size:
        raise RuntimeError("input/probe leak")
    return inputs, cue0, cue1, probes


impl.PROTOCOL = Path(__file__).resolve().parents[1] / "results" / "EXP-MEM-001" / "protocol_mapping_repair.md"
impl.make_input_map = repaired_make_input_map
impl.__file__ = __file__


if __name__ == "__main__":
    impl.main()
