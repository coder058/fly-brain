import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "harness"))
import sugar_calibrated as C  # noqa: E402


def test_bisection_finds_the_gain_that_matches_the_target():
    true = 0.17
    measure = lambda s: 500.0 * (s / true) ** 4  # noqa: E731  steep, monotone, like spread
    s, hist = C.bisect_scale(measure, target=500.0)
    assert len(hist) == 8
    assert abs(np.log(s / true)) < 0.05


def test_per_trial_active_counts_each_trial_separately():
    counts = np.array([[1, 0], [0, 2], [0, 0]])
    assert C.per_trial_active(counts) == 1.0
