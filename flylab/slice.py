"""The bundled E1 slice: the 500 highest out-degree neurons of the traced MaleCNS graph.

`data/e1_slice/e1_slice_500.npz` (70 KB, CC-BY 4.0, Janelia FlyEM) is exactly the induced
subgraph every E1 experiment ran on, so the demo and tests can use real connectome data
without the 1 GB download. `scripts/download_malecns.py` + `scripts/build_graph.py` rebuild
it from the raw files; `flylab.slice.from_full_graph` re-extracts it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import sparse

SLICE_DIR = Path(__file__).resolve().parents[1] / "data" / "e1_slice"
SLICE_NPZ = SLICE_DIR / "e1_slice_500.npz"


@dataclass
class Slice:
    src: np.ndarray            # presynaptic index in 0..n-1
    dst: np.ndarray            # postsynaptic index in 0..n-1
    signed_weight: np.ndarray  # synapse count x sign of the presynaptic neuron (UNKNOWN -> 0)
    body_id: np.ndarray        # MaleCNS body IDs, for attribution and lookup
    n: int

    def W(self) -> sparse.csr_matrix:
        """Signed (post, pre) matrix, ready for `W @ spikes`."""
        return sparse.csr_matrix((self.signed_weight.astype(np.float32), (self.dst, self.src)),
                                 shape=(self.n, self.n))


def load_slice(path: Path = SLICE_NPZ, verify: bool = True) -> Slice:
    if verify:
        meta = json.loads(path.with_suffix(".json").read_text())
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != meta["sha256"]:
            raise RuntimeError(f"{path.name}: sha256 {got} != recorded {meta['sha256']}")
    z = np.load(path)
    return Slice(src=z["src"].astype(np.int64), dst=z["dst"].astype(np.int64),
                 signed_weight=z["signed_weight"], body_id=z["body_id"], n=len(z["body_id"]))


def from_full_graph(g, n: int = 500) -> Slice:
    """Same selection rule as the E1 harness: top-n out-degree, sorted by graph index."""
    nodes = np.sort(np.argsort(np.diff(g.csr.indptr))[-n:])
    mask = np.isin(g.src, nodes) & np.isin(g.dst, nodes)
    remap = -np.ones(g.n, dtype=np.int64)
    remap[nodes] = np.arange(n)
    body = g.body_ids[nodes] if g.body_ids is not None else nodes
    return Slice(src=remap[g.src[mask]], dst=remap[g.dst[mask]],
                 signed_weight=g.signed_weight[mask].astype(np.float32), body_id=body, n=n)
