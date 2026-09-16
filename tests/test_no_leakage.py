"""The bug this file exists for: probes included driven input neurons, whose spike
timing IS the class label, so every arm scored ~0.76 through a silent network."""
import numpy as np
import pytest

import e1_reservoir as H


def test_probe_set_excludes_input_ids():
    n = 500
    inputs = np.random.default_rng(1).choice(n, size=50, replace=False)
    probes, pool = H.probe_set(n, input_ids=inputs, n_probes=48)
    assert len(np.intersect1d(probes, inputs)) == 0
    assert len(pool) == n - len(inputs)
    assert len(probes) == 48


def test_probe_set_without_input_ids_can_include_inputs():
    """Documents the unsafe call. Kept so the regression is visible, not silent."""
    n = 500
    inputs = np.random.default_rng(1).choice(n, size=50, replace=False)
    probes, _ = H.probe_set(n, input_ids=None, n_probes=48)
    assert len(np.intersect1d(probes, inputs)) > 0


def test_probe_set_is_deterministic():
    a, _ = H.probe_set(500, input_ids=np.arange(50), n_probes=48)
    b, _ = H.probe_set(500, input_ids=np.arange(50), n_probes=48)
    assert np.array_equal(a, b)


def test_simulate_driven_features_never_touch_driven_neurons(toy_csr):
    """Drive a fixed set at a level that guarantees they spike; with input_ids passed the
    features must be identical to a run where the driven rows are overwritten with garbage."""
    from flylab.dynamics import LIFParams

    n = toy_csr.shape[0]
    rng = np.random.default_rng(3)
    inputs = rng.choice(n, size=10, replace=False)
    T = 32
    I = np.zeros((T, n), dtype=np.float32)
    I[:, inputs] = 5.0
    p = LIFParams(tau_m=6.0, syn_scale=0.0)  # no coupling: driven set is the only active set

    X, stats = H.simulate_driven(toy_csr, I, p, seed=0, input_ids=inputs, return_stats=True)
    assert stats["driven_spikes"] > 0, "test is vacuous unless the driven set actually spikes"
    assert stats["pool_spikes"] == 0.0
    assert np.all(X == 0.0), "probes picked up driven activity through a decoupled network"
