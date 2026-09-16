"""Seeding must be reproducible: same seed -> identical features, different seed -> different."""
import numpy as np

import e1_reservoir as H
from flylab.dynamics import LIFParams


def _drive(n, T=32, seed=0, n_in=10):
    rng = np.random.default_rng(seed)
    inputs = rng.choice(n, size=n_in, replace=False)
    I = np.zeros((T, n), dtype=np.float32)
    I[:, inputs] = 4.0
    I += rng.normal(0, 0.3, size=I.shape).astype(np.float32)
    return [I, I.copy()], inputs


LIVE = LIFParams(tau_m=6.0, syn_scale=0.5)  # above the toy graph's ignition point


def test_reservoir_features_reproducible(toy_csr):
    n = toy_csr.shape[0]
    I_list, inputs = _drive(n)
    X1, s1 = H.reservoir_features(toy_csr, I_list, LIVE, seed=11, input_ids=inputs)
    X2, s2 = H.reservoir_features(toy_csr, I_list, LIVE, seed=11, input_ids=inputs)
    assert s1["pool_spikes"] > 0, "vacuous on a silent reservoir"
    assert np.array_equal(X1, X2)
    assert s1 == s2


def test_reservoir_features_seed_sensitive(toy_csr):
    n = toy_csr.shape[0]
    I_list, inputs = _drive(n)
    X1, s = H.reservoir_features(toy_csr, I_list, LIVE, seed=11, input_ids=inputs)
    X2, _ = H.reservoir_features(toy_csr, I_list, LIVE, seed=12, input_ids=inputs)
    assert s["pool_spikes"] > 0, "vacuous on a silent reservoir"
    assert not np.array_equal(X1, X2)


def test_make_trials_reproducible():
    cfg = H.load_cfg()
    a = H.make_trials(200, cfg, np.random.default_rng(5))
    b = H.make_trials(200, cfg, np.random.default_rng(5))
    assert np.array_equal(np.stack(a[0]), np.stack(b[0]))
    assert np.array_equal(a[1], b[1]) and np.array_equal(a[2], b[2])
