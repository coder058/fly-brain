"""EXP-INST-001 smoke: injection, null, split, estimator, gate, schema. Not evidence."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/harness"))

import e1_reservoir as H
import exp_inst_001 as E
import positive_control as PC


def test_e1_measurement_config_is_48_0002_signed_12x60():
    """Do not silently pick a config. These numbers are the powered E1 settings."""
    assert E.N_PROBES == 48
    assert E.TARGET_RATE == 0.002
    assert E.N_SEEDS == 12
    assert E.SEEDS == list(range(12))
    assert E.N_TRIALS == 60
    assert E.TARGET_EFFECT == 0.15
    assert E.MIN_EFFECT == 0.10
    assert E.MIN_EFFECT == PC.MIN_EFFECT
    cfg = json.loads((ROOT / "experiments/harness/e1_config.json").read_text())
    assert "n_probes" not in cfg
    assert "target_rate" not in cfg
    import inspect
    sig = inspect.signature(H.simulate_driven)
    assert sig.parameters["n_probes"].default == 48


def test_gate_not_weakened():
    tiny = E.gate_from_pairs([0.51] * 6, [0.50] * 6)
    assert tiny["separated"] is False
    clean = E.gate_from_pairs(
        [0.80, 0.78, 0.82, 0.79, 0.81, 0.80], [0.60] * 6
    )
    assert clean["separated"] is True
    assert clean["min_effect"] == 0.10


def test_split_has_no_overlap_and_matches_e1_cut():
    y = np.repeat(np.arange(5), 60)
    tr, te = E.split_indices(y)
    assert set(tr).isdisjoint(set(te))
    assert len(tr) + len(te) == len(y)
    for c in range(5):
        idx = np.where(y == c)[0]
        cut = int(0.7 * len(idx))
        assert np.array_equal(tr[y[tr] == c], idx[:cut])
        assert np.array_equal(te[y[te] == c], idx[cut:])


def test_theory_sigma_is_locked_to_e1_rate_and_bins():
    s = E.theory_sigma()
    assert abs(s - np.sqrt(0.002 * 0.998 / 16.0)) < 1e-12
    # independent of any feature matrix
    assert E.theory_sigma(0.002, 64, 4) == s


def test_injection_does_not_use_test_for_sigma():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(100, 16))
    y = np.repeat(np.arange(5), 20)
    tr, te = E.split_indices(y)
    s1 = E.train_sigma(X, tr)
    X2 = X.copy()
    X2[te] += 50.0
    s2 = E.train_sigma(X2, tr)
    assert s1 == s2


def test_templates_independent_of_features():
    t1 = E.class_templates(192, 5, np.random.default_rng(E.INJECTION_STREAM))
    t2 = E.class_templates(192, 5, np.random.default_rng(E.INJECTION_STREAM))
    assert np.allclose(t1, t2)
    g = t1 @ t1.T
    assert np.allclose(g, np.eye(5), atol=1e-8)


def test_null_permutation_preserves_counts_breaks_pairing():
    y = np.repeat(np.arange(5), 60)
    yp = np.random.default_rng([E.NULL_PERM_STREAM, 0, 0]).permutation(y)
    assert sorted(yp.tolist()) == sorted(y.tolist())
    assert not np.array_equal(yp, y)


def test_synthetic_calibration_locks_near_target():
    templates = E.class_templates(192, 5, np.random.default_rng(E.INJECTION_STREAM))
    cal = E.calibrate_amplitude(templates, 192, 5, 60, target=0.15, n_cal_seeds=8)
    assert cal["ok"]
    assert abs(cal["calibrated_mean_delta"] - 0.15) < 0.04
    assert cal["alpha_star"] > 0
    assert cal["delta_at_0"] < 0.08


def test_null_injection_does_not_manufacture_a_gate_pass_on_gaussians():
    templates = E.class_templates(64, 5, np.random.default_rng(1))
    rng = np.random.default_rng(2)
    pos, n0, n1 = [], [], []
    for s in range(8):
        X = rng.normal(size=(5 * 40, 64))
        y = np.repeat(np.arange(5), 40)
        tr, te = E.split_indices(y)
        yp0 = np.random.default_rng([3, s]).permutation(y)
        yp1 = np.random.default_rng([4, s]).permutation(y)
        n0.append(E.score_features(E.inject(X, yp0, templates, 1.5, 1.0), y, tr, te, 5, s)["acc"])
        n1.append(E.score_features(E.inject(X, yp1, templates, 1.5, 1.0), y, tr, te, 5, s)["acc"])
        pos.append(E.score_features(E.inject(X, y, templates, 1.5, 1.0), y, tr, te, 5, s)["acc"])
    null_gate = E.gate_from_pairs(n0, n1)
    pos_gate = E.gate_from_pairs(pos, n0)
    assert null_gate["separated"] is False
    assert pos_gate["mean_diff"] > 0.05


def test_ridge_sweep_selects_on_train_only():
    rng = np.random.default_rng(0)
    y = np.repeat(np.arange(5), 40)
    tr, te = E.split_indices(y)
    X = rng.normal(size=(len(y), 32))
    X[np.arange(len(y)), y] += 3.0
    r = H.ridge_sweep(X[tr], y[tr], X[te], y[te], 5, seed=0)
    assert r["selected_by"].startswith("validation split of train")
    assert "acc" in r


def test_aggregate_schema_and_dead_exclusion():
    def row(seed, alive, dpos, dnull=0.0):
        return {
            "seed": seed,
            "alive": alive,
            "probe_input_leak": False,
            "acc_no_injection": 0.2,
            "acc_positive": 0.4 + dpos,
            "acc_null_perm0": 0.25,
            "acc_null_perm_b": 0.25 + dnull,
            "diff_positive_vs_null0": 0.15 + dpos,
            "diff_null_pair": dnull,
            "realised_rate": 0.002,
            "null_perm_accs": [0.25] * E.N_NULL_PERMS,
        }
    live_rows = [row(i, True, 0.0) for i in range(12)]
    agg = E.aggregate(live_rows, alpha=1.0)
    assert agg["n_live"] == 12
    assert agg["power_floor_met"] is True
    assert "INSTRUMENT_VALID_E1" in agg
    assert agg["positive_vs_null"]["min_effect"] == 0.10
    dead_one = [row(0, False, 0.0)] + [row(i, True, 0.0) for i in range(1, 12)]
    agg_d = E.aggregate(dead_one, alpha=1.0)
    assert agg_d["n_live"] == 11
    assert agg_d["power_floor_met"] is False
    assert agg_d["INSTRUMENT_VALID_E1"] is False


def test_recorded_dead_reason_overrides_legacy_alive_flag():
    rows = []
    for seed in range(12):
        r = {
            "seed": seed, "alive": True, "probe_input_leak": False,
            "liveness": {"alive": True}, "acc_no_injection": 0.2,
            "acc_positive": 0.8, "acc_null_perm0": 0.5,
            "acc_null_perm_b": 0.5, "diff_positive_vs_null0": 0.3,
            "diff_null_pair": 0.0, "realised_rate": 0.002,
            "null_perm_accs": [0.5] * E.N_NULL_PERMS,
        }
        rows.append(r)
    rows[5]["liveness"]["dead_reason"] = "feature_std below guard"
    agg = E.aggregate(rows, alpha=1.0)
    assert agg["dead_seeds"] == [5]
    assert agg["n_live"] == 11
    assert agg["INSTRUMENT_VALID_E1"] is False


def test_smoke_synthetic_schema():
    templates = E.class_templates(192, 5, np.random.default_rng(0))
    s = E.run_smoke_synthetic(templates, 192, 5)
    assert s["status"] == "ok"
    assert s["split_disjoint"] is True
    assert s["gate_tiny_separated"] is False
    assert s["estimator"] == "ridge_sweep"
