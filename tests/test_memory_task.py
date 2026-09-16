"""EXP-MEM task smoke tests; no graph run and no scientific evidence."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/harness"))

from memory_task import (combine_split_liveness, delay_line_recall,
                         make_binary_trials)


def test_cue_only_at_onset_and_splits_have_balanced_labels():
    inputs = np.array([1, 3, 5])
    train, y_train = make_binary_trials(8, inputs, 6, 4, 6.0, 17)
    test, y_test = make_binary_trials(8, inputs, 6, 4, 6.0, 23)
    assert np.array_equal(np.bincount(y_train), [6, 6])
    assert np.array_equal(np.bincount(y_test), [6, 6])
    assert np.count_nonzero(train[:, 1:, :]) == 0
    assert np.count_nonzero(test[:, 1:, :]) == 0
    assert not np.array_equal(train, test)


def test_delay_line_is_a_known_memory_positive_control():
    assert delay_line_recall(1, 0, 4) == 1
    assert delay_line_recall(1, 4, 4) == 1
    assert delay_line_recall(1, 5, 4) == 0


def test_liveness_requires_train_and_test_splits_independently():
    summary = {"alive": True, "feature_std": 0.5}
    train = {"alive": True}
    test = {"alive": False, "dead_reason": "constant test features"}
    result = combine_split_liveness(summary, train, test)
    assert result["alive"] is False
    assert result["failed_splits"] == ["test"]
