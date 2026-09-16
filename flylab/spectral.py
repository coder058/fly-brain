"""Spectral normalisation of reservoir weights.

The E1 harness originally used a single hand-tuned `syn_scale` for every arm. That makes
the effective recurrent gain an accident of each graph's weight scale rather than a
controlled variable: on the 500-node MaleCNS subgraph rho(W) is 2131.9 for the connectome
and 43.2 for the size-matched Erdos-Renyi null, a 49x difference, so the two arms were
being run at wildly different operating points and compared as if they were not.

Effective per-step operator in the LIF membrane update
    dv = (-(v - v_rest) + r * (syn_scale * W @ s + I)) * dt / tau_m
is G = (dt * r / tau_m) * syn_scale * W, so rho(G) = (dt * r / tau_m) * syn_scale * rho(W).
`syn_scale_for_gain` inverts that.
"""
from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import ArpackNoConvergence, eigs

DENSE_MAX_N = 1500


def spectral_radius(W: sparse.spmatrix, signed: bool = True) -> float:
    """max |eigenvalue| of W (signed=False uses |W|, the excitatory-only upper bound)."""
    M = W if signed else abs(W)
    n = M.shape[0]
    if n <= DENSE_MAX_N:
        return float(np.max(np.abs(np.linalg.eigvals(np.asarray(M.todense(), dtype=np.float64)))))
    try:
        return float(np.max(np.abs(eigs(M.astype(np.float64), k=1, which="LM",
                                        return_eigenvectors=False, maxiter=5000))))
    except ArpackNoConvergence as exc:
        vals = exc.eigenvalues
        if len(vals):
            return float(np.max(np.abs(vals)))
        raise


def dominant_eigenvalue(W: sparse.spmatrix) -> complex:
    """Signed dominant eigenvalue. Its sign matters: a large negative real eigenvalue means
    the graph is inhibition-dominated, so rho=1 is an alternating instability rather than
    the excitatory ignition point that reservoir-computing intuition assumes."""
    n = W.shape[0]
    if n <= DENSE_MAX_N:
        ev = np.linalg.eigvals(np.asarray(W.todense(), dtype=np.float64))
        return complex(ev[np.argmax(np.abs(ev))])
    ev = eigs(W.astype(np.float64), k=1, which="LM", return_eigenvectors=False, maxiter=5000)
    return complex(ev[0])


def syn_scale_for_gain(rho: float, gain: float, tau_m: float, dt: float = 1.0,
                       r: float = 1.0) -> float:
    """syn_scale that puts the effective per-step operator at spectral radius `gain`."""
    if rho <= 0:
        raise ValueError(f"cannot normalise a graph with rho={rho}")
    return float(gain * tau_m / (dt * r * rho))


def effective_gain(rho: float, syn_scale: float, tau_m: float, dt: float = 1.0,
                   r: float = 1.0) -> float:
    """Inverse of syn_scale_for_gain: the gain a given syn_scale actually produces."""
    return float(rho * syn_scale * dt * r / tau_m)


def gain_for_target_rate(rate_fn, target_rate: float, lo: float = 0.05, hi: float = 60.0,
                         tol: float = 0.15, max_iter: int = 24) -> dict:
    """Bisect gain until `rate_fn(gain)` lands within `tol` (relative) of `target_rate`.

    Matched spectral radius does not imply matched activity: on the E1 subgraph the four arms
    fire 128 / 2419 / 7482 / 705 non-input spikes at the same gain of 1.0. Comparing graphs at
    matched firing rate is what isolates structure from excitability.
    """
    r_lo, r_hi = rate_fn(lo), rate_fn(hi)
    if r_lo > target_rate:
        return {"gain": lo, "rate": r_lo, "converged": False, "reason": "target below floor"}
    if r_hi < target_rate:
        return {"gain": hi, "rate": r_hi, "converged": False, "reason": "target above ceiling"}
    best = {"gain": hi, "rate": r_hi, "converged": False, "reason": "max_iter"}
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        r = rate_fn(mid)
        if abs(r - target_rate) <= tol * target_rate:
            return {"gain": mid, "rate": r, "converged": True}
        if r < target_rate:
            lo = mid
        else:
            hi = mid
        if abs(r - target_rate) < abs(best["rate"] - target_rate):
            best = {"gain": mid, "rate": r, "converged": False, "reason": "max_iter"}
    return best


def arm_spectrum(W: sparse.spmatrix) -> dict:
    lam = dominant_eigenvalue(W)
    return {
        "rho_signed": spectral_radius(W, signed=True),
        "rho_abs": spectral_radius(W, signed=False),
        "dominant_eigenvalue_real": float(lam.real),
        "dominant_eigenvalue_imag": float(lam.imag),
        "nnz": int(W.nnz),
    }
