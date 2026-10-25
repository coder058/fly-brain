import numpy as np
import pytest
from scipy import sparse

from flylab.brain import DEFAULTS, BrainModel, shiu_sign


def _random_net(n=40, p=0.25, seed=0):
    rng = np.random.default_rng(seed)
    mask = rng.random((n, n)) < p
    np.fill_diagonal(mask, False)
    counts = rng.integers(1, 30, size=(n, n)) * mask
    signs = np.where(rng.random(n) < 0.3, -1, 1)  # per presynaptic neuron (Dale)
    W = counts * signs[None, :]  # (post, pre)
    return sparse.csr_matrix(W.astype(float))


def test_subthreshold_dynamics_match_the_closed_form():
    """One neuron, one synaptic event: v follows the exact alpha-like solution."""
    p = DEFAULTS
    W = sparse.csr_matrix(np.array([[0.0, 10.0], [0.0, 0.0]]))  # 1 -> 0, 10 synapses
    m = BrainModel(W)
    steps = 400
    ev = np.zeros((steps, 1, 1), dtype=bool)
    ev[0] = True  # neuron 1 is kicked over threshold at step 0, spikes at step 1
    counts, times = m.simulate([1], n_trials=1, t_run=steps * p["dt"], record_spike_times=True,
                               poisson_events=ev)
    assert counts[1, 0] == 1 and counts[0, 0] == 0
    (t_spk, _, _), = times
    assert t_spk == 1
    # g of neuron 0 jumps by 10 * w_syn at step t_spk + delay; v then rises and decays
    g0 = 10 * p["w_syn"]
    t = np.arange(1, 200) * p["dt"]
    v_expected = p["v_0"] + g0 * p["tau"] / (p["tau"] - p["t_mbr"]) * (
        np.exp(-t / p["tau"]) - np.exp(-t / p["t_mbr"]))
    assert v_expected.max() < p["v_th"]  # stays subthreshold, as the count says


def test_delay_and_refractory_are_exact():
    p = DEFAULTS
    W = sparse.csr_matrix(np.array([[0.0, 200.0], [0.0, 0.0]]))  # strong 1 -> 0
    m = BrainModel(W)
    ev = np.zeros((300, 1, 1), dtype=bool)
    ev[0] = True
    _, times = m.simulate([1], n_trials=1, t_run=30.0, record_spike_times=True, poisson_events=ev)
    by_neuron = {}
    for t, rows, _ in times:
        for r in rows:
            by_neuron.setdefault(int(r), []).append(t)
    pre, post = by_neuron[1][0], by_neuron[0][0]
    # g arrives 18 steps after the presynaptic spike; v crosses threshold on a later step
    assert post > pre + m.delay_steps
    if len(by_neuron[0]) > 1:  # second spike only after the refractory window
        assert by_neuron[0][1] - by_neuron[0][0] > m.refractory_steps


def test_trials_are_independent_columns():
    W = _random_net()
    m = BrainModel(W)
    c_batch = m.simulate([0, 1, 2], n_trials=4, rate=150.0, seed=3, t_run=100.0)
    assert c_batch.shape == (40, 4)
    assert c_batch[[0, 1, 2]].sum() > 0
    assert len({tuple(c_batch[:, k]) for k in range(4)}) > 1  # different noise per trial


def test_silencing_removes_outgoing_effect():
    W = sparse.csr_matrix(np.array([[0.0, 300.0], [0.0, 0.0]]))
    m = BrainModel(W)
    on = m.simulate([1], n_trials=2, rate=200.0, seed=0, t_run=200.0)
    off = m.simulate([1], n_trials=2, rate=200.0, seed=0, t_run=200.0, silence=[1])
    assert on[0].sum() > 0 and off[0].sum() == 0


def test_shiu_sign_rule():
    assert shiu_sign("gaba") == -1 and shiu_sign("Glutamate") == -1
    assert all(shiu_sign(x) == 1 for x in ("acetylcholine", "dopamine", "serotonin", "octopamine"))


@pytest.mark.parametrize("net_seed,ev_seed,density", [(1, 5, 0.3), (2, 6, 0.15), (3, 7, 0.4)])
def test_spike_times_identical_to_brian2(net_seed, ev_seed, density):
    """Same equations written directly in Brian 2 (as in Shiu et al. model.py), same input
    events: every spike of every neuron must occur on the same time step."""
    b2 = pytest.importorskip("brian2")
    from brian2 import (Network, NeuronGroup, SpikeGeneratorGroup, SpikeMonitor, Synapses,
                        defaultclock, mV, ms, prefs, start_scope)

    prefs.codegen.target = "numpy"
    start_scope()
    p = DEFAULTS
    defaultclock.dt = p["dt"] * ms
    W = _random_net(n=40, p=density, seed=net_seed).toarray()
    exc = np.array([0, 1, 2, 3])
    steps = 1500
    rng = np.random.default_rng(ev_seed)
    ev = rng.random((steps, len(exc), 1)) < 0.03  # ~300 Hz of input events

    ns = dict(v_0=p["v_0"] * mV, v_rst=p["v_rst"] * mV, v_th=p["v_th"] * mV,
              t_mbr=p["t_mbr"] * ms, tau=p["tau"] * ms)
    neu = NeuronGroup(40, """dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)
                             dg/dt = -g / tau : volt (unless refractory)
                             rfc : second""",
                      threshold="v > v_th", reset="v = v_rst; g = 0 * mV", refractory="rfc",
                      method="linear", namespace=ns)
    neu.v = p["v_0"] * mV
    neu.g = 0 * mV
    neu.rfc = p["t_rfc"] * ms
    neu.rfc[exc] = 0 * ms
    pre, post = np.nonzero(W.T)  # W.T[pre, post]
    syn = Synapses(neu, neu, "w : volt", on_pre="g += w", delay=p["t_dly"] * ms)
    syn.connect(i=pre, j=post)
    syn.w = W[post, pre] * p["w_syn"] * mV
    t_idx, k_idx = np.nonzero(ev[:, :, 0])
    gen = SpikeGeneratorGroup(len(exc), k_idx, t_idx * p["dt"] * ms)
    kick = Synapses(gen, neu, on_pre=f"v_post += {p['w_syn'] * p['f_poi']} * mV")
    kick.connect(i=np.arange(len(exc)), j=exc)
    mon = SpikeMonitor(neu)
    Network(neu, syn, gen, kick, mon).run(steps * p["dt"] * ms)
    ref = sorted(zip(np.asarray(mon.i).tolist(),
                     np.round(np.asarray(mon.t / ms) / p["dt"]).astype(int).tolist(), strict=True))

    m = BrainModel(sparse.csr_matrix(W))
    _, times = m.simulate(exc, n_trials=1, t_run=steps * p["dt"], record_spike_times=True,
                          poisson_events=ev)
    ours = sorted((int(r), int(t)) for t, rows, _ in times for r in rows)
    assert len(ref) > 50
    assert ours == ref


@pytest.mark.parametrize("net_seed", [0, 4])
def test_fast_kernel_matches_batched_kernel(net_seed):
    from flylab.brain import _simulate_one

    W = _random_net(n=60, p=0.2, seed=net_seed)
    m = BrainModel(W)
    steps = 2000
    exc = np.array([0, 1, 2])
    ev = np.random.default_rng(net_seed).random((steps, 3, 1)) < 0.02
    _, t_batch = m.simulate(exc, n_trials=1, t_run=steps * 0.1, record_spike_times=True,
                            poisson_events=ev)
    Wc = m._W.tocsc()
    Wc.sort_indices()
    _, t_fast = _simulate_one(m, exc, 0.0, np.array([], dtype=np.int64), 0.0, Wc, 0, steps,
                              poisson_events=ev[:, :, 0], record_spike_times=True)
    a = sorted((int(r), int(t)) for t, rows, _ in t_batch for r in rows)
    b = sorted((int(r), int(t)) for t, rows in t_fast for r in rows)
    assert len(a) > 50 and a == b


def test_run_trials_is_reproducible_and_parallel_safe():
    from flylab.brain import run_trials

    m = BrainModel(_random_net(n=50, p=0.2, seed=2))
    c1 = run_trials(m, [0, 1], n_trials=3, rate=150.0, seed=9, t_run=100.0, workers=1)
    c2 = run_trials(m, [0, 1], n_trials=3, rate=150.0, seed=9, t_run=100.0, workers=2)
    assert c1.shape == (50, 3) and (c1 == c2).all() and c1.sum() > 0
