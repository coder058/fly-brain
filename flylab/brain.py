"""Whole-CNS leaky integrate-and-fire model with the dynamics of Shiu et al. (2024).

Shiu, P. K. et al. "A Drosophila computational brain model reveals sensorimotor processing",
Nature 634 (2024); code: github.com/philshiu/Drosophila_brain_model (MIT). Their model is
written in Brian 2. This module re-implements the same equations in vectorised NumPy/SciPy so
that many trials run as columns of one sparse product, and so that it can run on the
MaleCNS connectome as well as on the FlyWire connectome they used.

Per neuron (Brian 2 `method='linear'`, so integrated exactly over each step dt):

    dv/dt = (v_0 - v + g) / t_mbr      (unless refractory)
    dg/dt = -g / tau                   (unless refractory)
    spike when v > v_th (and not refractory); then v = v_rst, g = 0, refractory for t_rfc
    a presynaptic spike adds w = sign * synapse_count * w_syn to the target's g, t_dly later;
    input arriving while the target is refractory is lost (as it is in Brian 2)

Activated neurons get Poisson events at rate r_poi that add w_syn * f_poi straight to v and
have no refractory period, as in the original `PoissonInput`.

Within a step the order follows Brian 2's default schedule (groups → thresholds → synapses
→ resets): integrate, detect spikes, deliver delayed synaptic events and Poisson events,
then reset the neurons that spiked. Equivalence with Brian 2 on small networks is tested in
`tests/test_brain.py` when Brian 2 is installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import sparse

DEFAULTS = {  # Shiu et al. default_params, same units (mV, ms, Hz)
    "t_run": 1000.0, "n_run": 30,
    "v_0": -52.0, "v_rst": -52.0, "v_th": -45.0, "t_mbr": 20.0,
    "tau": 5.0, "t_rfc": 2.2, "t_dly": 1.8, "w_syn": 0.275,
    "r_poi": 150.0, "r_poi2": 0.0, "f_poi": 250.0, "dt": 0.1,
}


@dataclass
class BrainModel:
    """W_post_pre[i, j] = signed synapse count from neuron j onto neuron i."""

    W_post_pre: sparse.csr_matrix
    params: dict = field(default_factory=lambda: dict(DEFAULTS))

    def __post_init__(self):
        p = {**DEFAULTS, **self.params}
        self.params = p
        self.n = self.W_post_pre.shape[0]
        # Column access is what event-driven delivery needs: the targets of a spiking neuron.
        self._W = (self.W_post_pre.astype(np.float64) * p["w_syn"]).tocsc()
        dt = p["dt"]
        self.delay_steps = int(round(p["t_dly"] / dt))
        self.refractory_steps = int(round(p["t_rfc"] / dt))
        # Exact one-step propagator of the linear (v, g) system.
        a = np.exp(-dt / p["t_mbr"])
        b = np.exp(-dt / p["tau"])
        if np.isclose(p["tau"], p["t_mbr"]):
            c = (dt / p["t_mbr"]) * a
        else:
            c = p["tau"] / (p["tau"] - p["t_mbr"]) * (b - a)
        self._a, self._b, self._c = a, b, c

    def simulate(self, exc, n_trials: int | None = None, rate: float | None = None,
                 exc2=(), rate2: float | None = None, silence=(), seed: int = 0,
                 t_run: float | None = None, record_spike_times: bool = False,
                 poisson_events=None, monitor=None):
        """Run `n_trials` independent trials in parallel; return spike counts (n, n_trials).

        `poisson_events` (testing only) replaces the Poisson draws with an explicit boolean
        array of shape (steps, len(exc), n_trials).
        """
        p = self.params
        B = int(n_trials or p["n_run"])
        steps = int(round((t_run or p["t_run"]) / p["dt"]))
        rate = p["r_poi"] if rate is None else rate
        rate2 = p["r_poi2"] if rate2 is None else rate2
        exc = np.asarray(exc, dtype=np.int64)
        exc2 = np.asarray(exc2, dtype=np.int64)
        W = self._W
        if len(silence):
            # As in the original: zero every synapse *from* a silenced neuron.
            keep = np.ones(self.n)
            keep[np.asarray(silence, dtype=np.int64)] = 0.0
            W = (W @ sparse.diags(keep)).tocsc()
        rng = np.random.default_rng(seed)
        v = np.full((self.n, B), p["v_0"])
        g = np.zeros((self.n, B))
        # Brian 2 refractoriness: the threshold step recomputes `not_refractory` from the last
        # spike and clears it for neurons that just spiked; the state update of the *next*
        # step uses that flag. Poisson-driven neurons have t_rfc = 0.
        refr_steps = np.full(self.n, self.refractory_steps, dtype=np.int64)
        refr_steps[exc] = 0
        refr_steps[exc2] = 0
        lastspike = np.full((self.n, B), -(10 ** 9), dtype=np.int64)
        not_refr = np.ones((self.n, B), dtype=bool)
        ring = [None] * (self.delay_steps + 1)  # spikes waiting to be delivered
        counts = np.zeros((self.n, B), dtype=np.int32)
        times = [] if record_spike_times else None
        kick = p["w_syn"] * p["f_poi"]
        p1 = rate * p["dt"] * 1e-3
        p2 = rate2 * p["dt"] * 1e-3
        a, b, c = self._a, self._b, self._c
        mon = None if monitor is None else np.asarray(monitor, dtype=np.int64)
        trace = {"v": [], "g": []} if mon is not None else None
        for t in range(steps):
            # groups: exact linear update, frozen while refractory
            v_new = p["v_0"] + a * (v - p["v_0"]) + c * g
            g_new = b * g
            v = np.where(not_refr, v_new, v)
            g = np.where(not_refr, g_new, g)
            # thresholds
            not_refr = (t - lastspike) >= refr_steps[:, None]
            spk = (v > p["v_th"]) & not_refr
            # synapses: events from spikes t_dly ago, then Poisson input onto v
            due = ring[t % len(ring)]
            if due is not None:
                # Brian 2 drops synaptic input to `(unless refractory)` variables of neurons
                # that are refractory at delivery time (verified spike-for-spike in tests).
                g += (W @ due).toarray() * not_refr
            if len(exc) and (p1 > 0 or poisson_events is not None):
                ev = poisson_events[t] if poisson_events is not None else rng.random((len(exc), B)) < p1
                v[exc] += kick * ev
            if len(exc2) and p2 > 0:
                v[exc2] += kick * (rng.random((len(exc2), B)) < p2)
            # resets
            slot = (t + self.delay_steps) % len(ring)
            if spk.any():
                v[spk] = p["v_rst"]
                g[spk] = 0.0
                lastspike[spk] = t
                not_refr[spk] = False
                counts += spk
                if times is not None:
                    nz = np.nonzero(spk)
                    times.append((t, nz[0], nz[1]))
                ring[slot] = sparse.csc_matrix(spk.astype(np.float64))
            else:
                ring[slot] = None
            if trace is not None:  # same point in the step as a Brian 2 StateMonitor (end)
                trace["v"].append(v[mon, 0].copy())
                trace["g"].append(g[mon, 0].copy())
        if trace is not None:
            self.last_trace = {k: np.array(x) for k, x in trace.items()}
        if record_spike_times:
            return counts, times
        return counts

    def rates_hz(self, counts, t_run: float | None = None) -> np.ndarray:
        """Mean firing rate per neuron over trials, in Hz."""
        return counts.mean(axis=1) / ((t_run or self.params["t_run"]) * 1e-3)


SHIU_INHIBITORY = ("gaba", "glutamate")


def shiu_sign(nt: str, inhibitory=SHIU_INHIBITORY) -> int:
    """Shiu et al. sign rule, verified on their FlyWire 630 table: GABA and glutamate are
    inhibitory, every other transmitter (incl. dopamine, serotonin, octopamine) excitatory.
    `inhibitory` overrides the set, e.g. to add histamine (absent from FlyWire's classifier)."""
    return -1 if str(nt).lower() in inhibitory else 1


def _simulate_one(model: "BrainModel", exc, rate, exc2, rate2, W, seed, steps,
                  poisson_events=None, record_spike_times=False):
    """Single-trial kernel that only touches neurons away from rest.

    A neuron at exactly (v_0, g = 0, not refractory) and not Poisson-driven stays there until
    a synaptic event reaches it, so it can be skipped. Neurons rejoin the active set when an
    event arrives and leave it once |v - v_0| and |g| fall below 1e-12 mV outside their
    refractory window (they are then set exactly to rest). Equivalent to the batched kernel
    and to Brian 2 in the tests.
    """
    p = model.params
    n = model.n
    a, b, c = model._a, model._b, model._c
    v0, vth, vrst = p["v_0"], p["v_th"], p["v_rst"]
    rng = np.random.default_rng(seed)
    exc = np.asarray(exc, dtype=np.int64)
    exc2 = np.asarray(exc2, dtype=np.int64)
    driven = np.union1d(exc, exc2)
    v = np.full(n, v0)
    g = np.zeros(n)
    refr_steps = np.full(n, model.refractory_steps, dtype=np.int64)
    refr_steps[driven] = 0
    lastspike = np.full(n, -(10 ** 9), dtype=np.int64)
    not_refr = np.ones(n, dtype=bool)
    in_active = np.zeros(n, dtype=bool)
    in_active[driven] = True
    A = driven.copy()
    indptr, indices, data = W.indptr, W.indices, W.data
    ring = [None] * (model.delay_steps + 1)
    counts = np.zeros(n, dtype=np.int32)
    times = [] if record_spike_times else None
    kick = p["w_syn"] * p["f_poi"]
    p1 = rate * p["dt"] * 1e-3
    p2 = rate2 * p["dt"] * 1e-3
    eps = 1e-12
    for t in range(steps):
        # groups
        nr = not_refr[A]
        vA, gA = v[A], g[A]
        v[A] = np.where(nr, v0 + a * (vA - v0) + c * gA, vA)
        g[A] = np.where(nr, b * gA, gA)
        # thresholds (neurons outside A are at rest and not refractory)
        nrA = (t - lastspike[A]) >= refr_steps[A]
        not_refr[A] = nrA
        spk = A[(v[A] > vth) & nrA]
        # synapses
        due = ring[t % len(ring)]
        if due is not None and len(due):
            starts, ends = indptr[due], indptr[due + 1]
            lens = ends - starts
            idx = np.repeat(starts - np.cumsum(np.r_[0, lens[:-1]]), lens) + np.arange(lens.sum())
            rows = indices[idx]
            add = np.bincount(rows, weights=data[idx], minlength=0)
            hit = np.flatnonzero(add)
            g[hit] += add[hit] * not_refr[hit]
            new = hit[~in_active[hit]]
            if len(new):
                in_active[new] = True
                A = np.concatenate([A, new])
        if len(exc) and (p1 > 0 or poisson_events is not None):
            ev = poisson_events[t] if poisson_events is not None else rng.random(len(exc)) < p1
            v[exc] += kick * ev
        if len(exc2) and p2 > 0:
            v[exc2] += kick * (rng.random(len(exc2)) < p2)
        # resets
        slot = (t + model.delay_steps) % len(ring)
        if len(spk):
            v[spk] = vrst
            g[spk] = 0.0
            lastspike[spk] = t
            not_refr[spk] = False
            counts[spk] += 1
            if times is not None:
                times.append((t, spk.copy()))
        ring[slot] = spk if len(spk) else None
        # shrink the active set every 50 steps
        if t % 50 == 49:
            rest = (np.abs(v[A] - v0) < eps) & (np.abs(g[A]) < eps) & not_refr[A] \
                & ((t - lastspike[A]) >= refr_steps[A]) & ~np.isin(A, driven)
            if rest.any():
                gone = A[rest]
                v[gone] = v0
                g[gone] = 0.0
                in_active[gone] = False
                A = A[~rest]
    return counts, times


def _trial_worker(args):
    model, exc, rate, exc2, rate2, W, seed, steps = args
    return _simulate_one(model, exc, rate, exc2, rate2, W, seed, steps)[0]


def run_trials(model: BrainModel, exc, n_trials: int | None = None, rate: float | None = None,
               exc2=(), rate2: float | None = None, silence=(), seed: int = 0,
               t_run: float | None = None, workers: int = 1) -> np.ndarray:
    """Fast path: independent single-trial kernels, optionally across processes.

    Trial k uses RNG seed (seed, k). Returns spike counts of shape (n, n_trials)."""
    import multiprocessing as mp

    p = model.params
    B = int(n_trials or p["n_run"])
    steps = int(round((t_run or p["t_run"]) / p["dt"]))
    rate = p["r_poi"] if rate is None else rate
    rate2 = p["r_poi2"] if rate2 is None else rate2
    W = model._W
    if len(silence):
        keep = np.ones(model.n)
        keep[np.asarray(silence, dtype=np.int64)] = 0.0
        W = (W @ sparse.diags(keep)).tocsc()
    W = W.tocsc()
    W.sort_indices()
    jobs = [(model, exc, rate, exc2, rate2, W, [seed, k], steps) for k in range(B)]
    if workers > 1:
        with mp.get_context("fork").Pool(workers) as pool:
            cols = pool.map(_trial_worker, jobs)
    else:
        cols = [_trial_worker(j) for j in jobs]
    return np.stack(cols, axis=1)
