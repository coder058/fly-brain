"""The old guard only checked feature variance, so a silent reservoir read out through
driven input neurons sailed past it. Liveness must mean non-input spikes."""
import numpy as np
import pytest
from scipy import sparse

import e1_reservoir as H
from flylab.dynamics import LIFParams


def _silent_but_variable_features(n=120, T=32, n_in=12):
    """Exactly the failure mode: zero coupling, so nothing but the driven set ever fires."""
    W = sparse.csr_matrix((n, n), dtype=np.float32)
    rng = np.random.default_rng(0)
    inputs = rng.choice(n, size=n_in, replace=False)
    I_list = []
    for c in range(4):
        for _ in range(5):
            I = np.zeros((T, n), dtype=np.float32)
            I[4 + 5 * c : 9 + 5 * c, inputs] = 6.0
            I_list.append(I)
    return W, I_list, inputs


def test_leaky_probes_produce_variance_without_any_reservoir_activity():
    W, I_list, inputs = _silent_but_variable_features()
    p = LIFParams(tau_m=6.0, syn_scale=0.002)
    X_leak, s_leak = H.reservoir_features(W, I_list, p, seed=0, input_ids=None)
    assert s_leak["pool_spikes"] > 0  # only because inputs are inside the pool
    assert X_leak.std() > 1e-6, "old guard's variance check passes on pure leakage"

    X_clean, s_clean = H.reservoir_features(W, I_list, p, seed=0, input_ids=inputs)
    assert s_clean["pool_spikes"] == 0.0
    assert X_clean.std() == 0.0


def test_guard_raises_on_silent_reservoir():
    W, I_list, inputs = _silent_but_variable_features()
    cfg = H.load_cfg()
    p = LIFParams(tau_m=6.0, syn_scale=0.002)
    X, stats = H.reservoir_features(W, I_list, p, seed=0, input_ids=inputs)
    with pytest.raises(RuntimeError, match="reservoir silent"):
        H.check_alive(X, stats, "unit", cfg.get("harness_guards", {}))


def test_guard_records_instead_of_raising_when_asked():
    W, I_list, inputs = _silent_but_variable_features()
    p = LIFParams(tau_m=6.0, syn_scale=0.002)
    X, stats = H.reservoir_features(W, I_list, p, seed=0, input_ids=inputs)
    rep = H.check_alive(X, stats, "unit", {"reject_dead_features": True, "on_dead": "record"})
    assert rep["alive"] is False
    assert "dead_reason" in rep


def test_nonzero_spikes_do_not_override_failed_feature_guards():
    X = np.zeros((12, 3), dtype=np.float32)
    stats = {"pool_spikes": 1.0, "probe_spikes": 0.0}
    guards = {
        "reject_dead_features": True,
        "on_dead": "record",
        "min_non_input_spikes": 1,
        "min_feature_std": 1e-6,
        "min_unique_feature_rows": 8,
    }
    rep = H.check_alive(X, stats, "degenerate", guards)
    assert rep["non_input_active"] is True
    assert rep["alive"] is False
    assert "feature_std" in rep["dead_reason"]


def test_disabled_feature_guard_still_requires_non_input_activity():
    X = np.ones((12, 3), dtype=np.float32)
    rep = H.check_alive(X, {"pool_spikes": 0.0, "probe_spikes": 0.0}, "silent", {
        "reject_dead_features": False,
    })
    assert rep["alive"] is False
