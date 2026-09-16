"""Sparse MaleCNS graph loaders (derived artifacts only — never touch data/raw)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow.feather as feather
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = ROOT / "data/derived/graph"


@dataclass
class SparseGraph:
    """CSR/CSC unsigned + signed COO views. Indices are neuron_id in [0, n)."""

    csr: sparse.csr_matrix
    csc: sparse.csc_matrix
    src: np.ndarray
    dst: np.ndarray
    weight: np.ndarray
    sign_pre: np.ndarray
    signed_weight: np.ndarray
    meta: dict
    body_ids: np.ndarray | None = None

    @property
    def n(self) -> int:
        return int(self.csr.shape[0])

    @property
    def nnz(self) -> int:
        return int(self.csr.nnz)

    def signed_csr(self) -> sparse.csr_matrix:
        """Build CSR with signed_weight (UNKNOWN pre → 0)."""
        return sparse.csr_matrix(
            (self.signed_weight.astype(np.float32), (self.src, self.dst)),
            shape=self.csr.shape,
        )

    def abs_weight_csr(self) -> sparse.csr_matrix:
        """Ablation: drop E/I signs, keep |w| and topology."""
        return sparse.csr_matrix(
            (np.abs(self.weight).astype(np.float32), (self.src, self.dst)),
            shape=self.csr.shape,
        )


def load_meta(path: Path | None = None) -> dict:
    p = path or (GRAPH_DIR / "graph_meta.json")
    return json.loads(p.read_text())


def load_graph(graph_dir: Path | None = None, load_neurons: bool = True) -> SparseGraph:
    d = graph_dir or GRAPH_DIR
    meta = load_meta(d / "graph_meta.json")
    csr_npz = np.load(d / "csr_unsigned.npz")
    csc_npz = np.load(d / "csc_unsigned.npz")
    coo = np.load(d / "coo_signed.npz")

    csr = sparse.csr_matrix(
        (csr_npz["data"], csr_npz["indices"], csr_npz["indptr"]),
        shape=tuple(csr_npz["shape"]),
    )
    csc = sparse.csc_matrix(
        (csc_npz["data"], csc_npz["indices"], csc_npz["indptr"]),
        shape=tuple(csc_npz["shape"]),
    )

    body_ids = None
    neurons_path = d / "neurons.feather"
    if load_neurons and neurons_path.exists():
        body_ids = feather.read_table(neurons_path, columns=["body_id"])["body_id"].to_numpy()

    return SparseGraph(
        csr=csr,
        csc=csc,
        src=coo["src"],
        dst=coo["dst"],
        weight=coo["weight"],
        sign_pre=coo["sign_pre"],
        signed_weight=coo["signed_weight"],
        meta=meta,
        body_ids=body_ids,
    )


def induced_subgraph(g: SparseGraph, nodes: np.ndarray) -> tuple[sparse.csr_matrix, np.ndarray]:
    """Return signed CSR on `nodes` (renumbered 0..k-1) and the node index map."""
    nodes = np.asarray(nodes, dtype=np.int64)
    mask = np.isin(g.src, nodes) & np.isin(g.dst, nodes)
    remap = -np.ones(g.n, dtype=np.int64)
    remap[nodes] = np.arange(len(nodes), dtype=np.int64)
    s = remap[g.src[mask]]
    t = remap[g.dst[mask]]
    w = g.signed_weight[mask].astype(np.float32)
    mat = sparse.csr_matrix((w, (s, t)), shape=(len(nodes), len(nodes)))
    return mat, nodes
