"""PROTOCOL.md:24 requires baselines within +/-10% of the readout's parameter budget.
The original MLP had 6,341 parameters against a 965-parameter readout."""
import numpy as np
import pytest

import e1_reservoir as H


def test_readout_params_matches_the_documented_965():
    assert H.readout_params(48 * 4, 5) == 965


def test_mlp_width_lands_inside_the_protocol_budget():
    for d, n_classes in ((192, 5), (1800, 5), (64, 3)):
        budget = H.readout_params(d, n_classes)
        width, params, ok = H.mlp_width_for_budget(d, n_classes, budget)
        assert ok, f"d={d}: {params} vs budget {budget}"
        assert abs(params - budget) / budget <= 0.10
        assert width >= 1


def test_original_width32_mlp_is_out_of_budget():
    """Regression witness: the configuration the harness used to ship."""
    d, n_classes, width = 192, 5, 32
    params = width * (d + 1 + n_classes) + n_classes
    budget = H.readout_params(d, n_classes)
    assert params == 6341 and budget == 965
    assert params / budget > 6.0


def test_mlp_baseline_respects_the_budget():
    rng = np.random.default_rng(0)
    Xtr, ytr = rng.normal(size=(60, 192)), rng.integers(0, 5, size=60)
    Xte, yte = rng.normal(size=(20, 192)), rng.integers(0, 5, size=20)
    budget = H.readout_params(192, 5)
    _, params, info = H.mlp_baseline(Xtr, ytr, Xte, yte, 5, rng, steps=5,
                                     param_budget=budget)
    assert info["within_budget"] is True
    assert abs(params - budget) / budget <= 0.10


def test_ridge_sweep_reports_a_curve_and_never_selects_on_test():
    rng = np.random.default_rng(1)
    n, d = 120, 20
    y = rng.integers(0, 4, size=n)
    X = rng.normal(size=(n, d)) + np.eye(4)[y] @ rng.normal(size=(4, d)) * 2.0
    tr, te = np.arange(0, 90), np.arange(90, n)
    out = H.ridge_sweep(X[tr], y[tr], X[te], y[te], 4, seed=0)
    assert len(out["curve"]) == len(H.RIDGE_GRID)
    assert out["selected_ridge"] in H.RIDGE_GRID
    best_by_test = max(out["curve"], key=lambda c: c["test_acc"])
    assert out["selected_ridge"] == max(
        out["curve"], key=lambda c: (c["val_acc"], -c["ridge"])
    )["ridge"]
    assert all("train_test_gap" in c for c in out["curve"])
    # selection is allowed to miss the test-optimal ridge; that is the point of not peeking
    assert best_by_test["test_acc"] >= out["acc"] - 1e-9


def test_ridge_sweep_gap_shrinks_with_regularisation():
    rng = np.random.default_rng(2)
    n, d = 80, 60
    y = rng.integers(0, 4, size=n)
    X = rng.normal(size=(n, d))
    tr, te = np.arange(0, 60), np.arange(60, n)
    curve = H.ridge_sweep(X[tr], y[tr], X[te], y[te], 4, seed=0)["curve"]
    assert curve[0]["train_test_gap"] > curve[-1]["train_test_gap"]
