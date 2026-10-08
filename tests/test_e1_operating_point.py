import numpy as np

import e1_operating_point as OP
import e1_reservoir as H
from flylab.dynamics import LIFParams


def _drive(n, inputs, n_trials=3, T=24, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_trials):
        I = rng.normal(0, 0.5, size=(T, n)).astype(np.float32)
        I[:, inputs] += 4.0
        out.append(I)
    return out


def test_probe48_readout_is_bit_identical_to_original_harness(toy_csr):
    n = toy_csr.shape[0]
    inputs = np.arange(6)
    I_list = _drive(n, inputs)
    lif = LIFParams(tau_m=6.0, syn_scale=0.05)
    feats, st = OP.simulate_features(toy_csr, I_list, lif, seed=3, input_ids=inputs, n_probes=12)
    X_ref, st_ref = H.reservoir_features(toy_csr, I_list, lif, 3, input_ids=inputs, n_probes=12)
    np.testing.assert_array_equal(feats["probe48"], X_ref)
    assert st["pool_spikes"] == st_ref["pool_spikes"]
    assert st["probe_spikes"] == st_ref["probe_spikes"]


def test_full_readout_covers_every_non_input_neuron(toy_csr):
    n = toy_csr.shape[0]
    inputs = np.arange(6)
    feats, _ = OP.simulate_features(toy_csr, _drive(n, inputs), LIFParams(tau_m=6.0, syn_scale=0.05),
                                    seed=0, input_ids=inputs, n_probes=12)
    assert feats["full"].shape[1] == OP.N_BINS * (n - len(inputs))


def test_input_only_baseline_never_reads_non_input_neurons():
    n, T = 20, 16
    inputs = np.array([0, 1, 2])
    I = np.zeros((T, n), dtype=np.float32)
    I[:, 3:] = 99.0  # junk on non-input neurons must not leak into the baseline
    I[:4, inputs] = 1.0
    X = OP.input_only_features([I], inputs)
    np.testing.assert_allclose(X[0], [1.0, 0.0, 0.0, 0.0])


def test_paired_summary_excludes_off_target_rate_only_when_gated():
    rows = []
    for seed, (c_acc, rate_ok) in enumerate([(0.8, True), (0.2, False), (0.7, True)]):
        rows.append({"seed": seed, "arm": "connectome_signed", "draw": 0, "matching": "per_seed",
                     "readout": "full", "acc": c_acc, "alive": True, "rate_within_tol": rate_ok})
        for null in ("degree_preserving_null", "er_null"):
            rows.append({"seed": seed, "arm": null, "draw": 0, "matching": "per_seed",
                         "readout": "full", "acc": 0.5, "alive": True, "rate_within_tol": True})
    gated = OP.paired_summary(rows, [0, 1, 2], "per_seed", "full", require_rate=True)
    ungated = OP.paired_summary(rows, [0, 1, 2], "per_seed", "full", require_rate=False)
    assert gated["arms"]["connectome_signed"]["n_seeds"] == 2
    assert [e["seed"] for e in gated["excluded_seeds"]] == [1]
    assert ungated["arms"]["connectome_signed"]["n_seeds"] == 3
    c = gated["comparisons"]["connectome_vs_degree_preserving_null"]
    assert c["n"] == 2 and np.isclose(c["mean_diff"], 0.25)


def test_dual_ridge_matches_primal_solution():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(30, 80))
    y = rng.integers(0, 4, size=30)
    W_dual = H.fit_readout(X, y, 4, ridge=0.5)
    Xb = np.concatenate([X, np.ones((30, 1))], axis=1)
    W_primal = np.linalg.solve(Xb.T @ Xb + 0.5 * np.eye(81), Xb.T @ np.eye(4)[y])
    np.testing.assert_allclose(W_dual, W_primal, rtol=1e-8, atol=1e-10)
