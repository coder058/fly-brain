"""CPU-first LIF dynamics on sparse signed connectome weights.

UNKNOWN (sign=0) contributes 0 — never treated as excitatory.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse


@dataclass
class LIFParams:
    dt: float = 1.0
    tau_m: float = 20.0
    v_rest: float = 0.0
    v_reset: float = 0.0
    v_th: float = 1.0
    r: float = 1.0
    syn_scale: float = 1e-3  # scale synapse weights into membrane units


@dataclass
class LIFState:
    v: np.ndarray
    spikes: np.ndarray


def step_lif(
    W: sparse.spmatrix,
    state: LIFState,
    I_ext: np.ndarray,
    p: LIFParams,
) -> LIFState:
    """One Euler LIF step. W is signed CSR (rows=post, cols=pre) or (pre→post) as W @ spikes.

    Convention: current = W @ spikes_pre, with W[i,j] = signed weight j→i
    (scipy CSR built as (src=pre, dst=post) needs W.T for post-synaptic current).
    """
    # Our COO is (src=pre, dst=post); CSR from (src,dst) means A[pre,post].
    # Postsynaptic input for post i: sum_pre A[pre,i] * spike[pre] = (A.T @ spikes)[i]
    # Prefer passing W already as post×pre.
    syn = W @ state.spikes.astype(np.float32)
    dv = (-(state.v - p.v_rest) + p.r * (p.syn_scale * syn + I_ext)) * (p.dt / p.tau_m)
    v = state.v + dv
    spikes = (v >= p.v_th).astype(np.float32)
    v = np.where(spikes > 0, p.v_reset, v)
    return LIFState(v=v.astype(np.float32), spikes=spikes)


def simulate(
    W_post_pre: sparse.spmatrix,
    n_steps: int,
    I_ext: np.ndarray | None = None,
    p: LIFParams | None = None,
    seed: int = 0,
) -> dict:
    """Run LIF for n_steps. Returns spike raster (T,N) and mean rate."""
    p = p or LIFParams()
    n = W_post_pre.shape[0]
    rng = np.random.default_rng(seed)
    v0 = rng.normal(p.v_rest, 0.05, size=n).astype(np.float32)
    state = LIFState(v=v0, spikes=np.zeros(n, dtype=np.float32))
    if I_ext is None:
        I_ext = np.zeros(n, dtype=np.float32)
    raster = np.zeros((n_steps, n), dtype=np.float32)
    for t in range(n_steps):
        state = step_lif(W_post_pre, state, I_ext, p)
        raster[t] = state.spikes
    return {
        "raster": raster,
        "mean_rate": float(raster.mean()),
        "n_spikes": int(raster.sum()),
        "n": n,
        "n_steps": n_steps,
    }


def post_pre_from_pre_post(A_pre_post: sparse.spmatrix) -> sparse.csr_matrix:
    """Convert COO-built (pre,post) matrix to (post,pre) for W @ spikes_pre."""
    return A_pre_post.T.tocsr()
