import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "harness"))
import hd_memory as M  # noqa: E402
from flylab.slice import load_hd_circuit  # noqa: E402


def test_readout_pool_excludes_every_possible_input_neuron():
    _, neurons = load_hd_circuit()
    inputs, candidate, pool = M.build_task(neurons)
    assert len(inputs) == 8 and all(len(i) >= 2 for i in inputs)
    assert np.intersect1d(np.concatenate(inputs), pool).size == 0
    assert set(candidate) | set(pool) == set(range(len(neurons)))


def test_trial_noise_depends_on_trial_id_not_list_position():
    sl, neurons = load_hd_circuit()
    inputs, _, pool = M.build_task(neurons)
    cfg = dict(delays=[5], window=2, pulse_steps=2, pulse_amp=4.0, noise=0.6, tau_m=6.0)
    lif = M.lif_for(1.0, 3.0, cfg)
    labels = np.array([0, 3, 5])
    X_all, _ = M.features(sl.W(), lif, labels, inputs, pool, cfg, seed=7)
    X_one, _ = M.features(sl.W(), lif, labels[[2]], inputs, pool, cfg, seed=7, trial_ids=[2])
    np.testing.assert_array_equal(X_all[5][2], X_one[5][0])


def test_end_to_end_no_network_arm_is_at_chance_and_selection_ignores_test(tmp_path):
    import json

    M.main(["--seeds", "0", "--draws", "1", "--trials-per-class", "10", "--workers", "1",
            "--delays", "5", "--gains", "2,4", "--label", "test", "--out-dir", str(tmp_path)])
    (out,) = tmp_path.glob("hd_test_*.json")
    res = json.loads(out.read_text())
    rows = {r["arm"]: r for r in res["rows"]}
    assert set(rows) == {"connectome", "dale_degree_null", "topography_null", "no_network"}
    # gain is chosen from training-split validation; it must be on the grid
    assert all(r["gain"] in (2.0, 4.0) for r in rows.values() if r["acc"] is not None)
    nn = rows["no_network"]
    assert nn["acc"] is None or nn["acc"] <= 0.35
