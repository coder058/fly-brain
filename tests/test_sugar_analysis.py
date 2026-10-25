import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "harness"))
import sugar_analysis as A  # noqa: E402


def _cond(inp, rate, trials, types=None, each=None):
    return {"input": inp, "rate_hz": rate, "mn9_trials": list(trials), "mn9_mean": float(np.mean(trials)),
            "mn9_each": each, "active_neurons": int(rate) * 10, "type_rates": types}


def _write(tmp_path, label, conds, complete=True, stamp="20260101T000000Z"):
    res = {"label": label, "complete": complete, "conditions": conds}
    (tmp_path / f"sugar_{label}_{stamp}_abc.json").write_text(json.dumps(res))


def test_decision_rules_and_incomplete_runs_are_ignored(tmp_path):
    rng = np.random.default_rng(0)
    conds = {f"lb3c_both@{r}": _cond("lb3c_both", r, (r / 2 + rng.normal(0, 1, 30)).clip(0) if r else [0] * 30,
                                     types={"A": r / 4, "B": 0.0} if r == 200 else None)
             for r in (0, 50, 100, 150, 200)}
    conds["lb3c_both@200/dale_null0"] = dict(_cond("lb3c_both", 200, [0.0] * 30), null_draw=0)
    _write(tmp_path, "malecns-both", conds)
    # a later but incomplete file must not be picked up
    _write(tmp_path, "malecns-both", {"x@0": _cond("lb3c_both", 0, [50] * 30)}, complete=False,
           stamp="20270101T000000Z")
    fw = {f"lb3c_both@{r}": _cond("lb3c_both", r, [r / 3] * 30,
                                  types={"A": 10.0, "B": 2.0, "C": 1.0} if r == 200 else None)
          for r in (0, 200)}
    _write(tmp_path, "flywire", fw)
    assert A.main(["--dir", str(tmp_path)]) == 0
    out = json.loads((tmp_path / "analysis.json").read_text())
    assert out["primary"]["verdict"] == "replicates"
    assert out["primary"]["ci95"][0] > 90
    assert out["dose_response_malecns"]["spearman"] == pytest.approx(1.0)
    assert out["nulls"]["pathway_depends_on_wiring"] is True
    assert out["overlap"]["hits"] == ["A"]
    assert out["overlap"]["top_absent_in_malecns"] == ["C"]


def test_no_drive_does_not_replicate(tmp_path):
    conds = {f"lb3c_both@{r}": _cond("lb3c_both", r, [0.0] * 30) for r in (0, 200)}
    _write(tmp_path, "malecns-both", conds)
    assert A.primary(A.latest("malecns-both", tmp_path))["verdict"] == "does not replicate"
