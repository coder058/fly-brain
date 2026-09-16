"""MaleCNS subgraph reservoir anomaly scorer (reuse flylab dynamics)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from flylab.graph import load_graph, induced_subgraph
from flylab.dynamics import LIFParams, LIFState, step_lif, post_pre_from_pre_post
from flylab.spectral import arm_spectrum, syn_scale_for_gain


def select_top_nodes(g, n: int = 256):
    deg = np.diff(g.csr.indptr)
    return np.sort(np.argsort(deg)[-n:])


def encode_to_current(x_win: np.ndarray, n_neurons: int, input_ids: np.ndarray, amp: float = 3.0):
    T, C = x_win.shape
    I = np.zeros((T, n_neurons), dtype=np.float32)
    x = (x_win - x_win.mean()) / (x_win.std() + 1e-6)
    for t in range(T):
        for j, nid in enumerate(input_ids):
            I[t, int(nid)] = amp * float(x[t, j % C])
    return I


def make_W_post_pre(g, nodes: np.ndarray, mode: str = "signed"):
    """mode: signed | abs | er_null"""
    if mode in ("signed", "abs"):
        A, _ = induced_subgraph(g, nodes)  # signed CSR in (pre,post) indexing from graph.py
        # induced builds csr ((s,t)) with s=remap[src], t=remap[dst] → A[pre,post]
        if mode == "abs":
            A = sparse.csr_matrix((np.abs(A.data), A.indices, A.indptr), shape=A.shape)
        return post_pre_from_pre_post(A)
    # ER null matching nnz
    A, _ = induced_subgraph(g, nodes)
    nnz = A.nnz
    k = len(nodes)
    rng = np.random.default_rng(0)
    flat = rng.choice(k * (k - 1), size=min(nnz, k * (k - 1)), replace=False)
    src = flat // (k - 1)
    dst = flat % (k - 1)
    dst = dst + (dst >= src).astype(np.int64)
    w = rng.choice(np.array([-1.0, 1.0], dtype=np.float32), size=len(src)) * rng.uniform(1, 10, len(src)).astype(np.float32)
    A = sparse.csr_matrix((w, (src, dst)), shape=(k, k))
    return post_pre_from_pre_post(A)


def reservoir_embed(W_post_pre: sparse.csr_matrix, I: np.ndarray, lif: LIFParams):
    n = W_post_pre.shape[0]
    st = LIFState(v=np.zeros(n, dtype=np.float32), spikes=np.zeros(n, dtype=np.float32))
    rates = np.zeros(n, dtype=np.float32)
    for t in range(I.shape[0]):
        st = step_lif(W_post_pre, st, I[t], lif)
        rates += st.spikes
    rates /= max(I.shape[0], 1)
    return rates


def fit_mu(embeds: np.ndarray):
    return embeds.mean(0)


def anomaly_score(embeds: np.ndarray, mu: np.ndarray):
    return ((embeds - mu) ** 2).sum(1)
