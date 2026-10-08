#!/usr/bin/env python3
"""Read-only provenance audit for the registered MEM-002 artifacts."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEM_ROOT = ROOT / "experiments/results/EXP-MEM-002"
INST_CONCLUSION = ROOT / "experiments/results/EXP-INST-001/conclusion.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# The INST-001 conclusion was frozen at a01037d in the private lab history. That history was
# squashed into the public snapshot 6a60ff3, so a public clone cannot resolve a01037d; the
# audit then compares against the first public commit instead and says so in its output.
INST_BASELINE_REVS = ("a01037d", "6a60ff3")


def git_blob_hash(revision: str, path: str) -> str | None:
    """SHA-256 of `path` at `revision`, or None if the revision is not in this clone."""
    try:
        data = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None
    return hashlib.sha256(data).hexdigest()


def audit_run(run: Path) -> dict:
    stage = run / "q0"
    started = json.loads((stage / "stage_started.json").read_text())
    complete = json.loads((stage / "stage_complete.json").read_text())
    summary = json.loads((stage / "summary.json").read_text())
    protocol_hash = started["protocol_sha256"]
    runner_hash = started["runner_sha256"]
    cell_files = sorted(stage.glob("seed_*.json"))
    calibration_files = sorted(stage.glob("calibration_seed_*.json"))
    mismatches = []
    forbidden = []
    for path in calibration_files + cell_files:
        row = json.loads(path.read_text())
        if row.get("protocol_sha256") != protocol_hash or row.get("runner_sha256") != runner_hash:
            mismatches.append(path.name)
        if any(key in row for key in ("accuracy", "auc", "curve_by_arm")):
            forbidden.append(path.name)
    if complete["protocol_sha256"] != protocol_hash or complete["runner_sha256"] != runner_hash:
        mismatches.append("stage_complete.json")
    return {
        "run": run.name,
        "status": summary.get("status"),
        "cells": summary.get("cells_written"),
        "expected_cells": summary.get("expected_cells"),
        "complete_delays": summary.get("complete_delays"),
        "missing_rows": len(summary.get("missing_cells", [])),
        "cell_files": len(cell_files),
        "calibration_files": len(calibration_files),
        "provenance_mismatches": mismatches,
        "forbidden_metric_rows": forbidden,
        "protocol_sha256": protocol_hash,
        "runner_sha256": runner_hash,
    }


def audit() -> dict:
    runs = [path for path in sorted(MEM_ROOT.glob("q0_*")) if (path / "q0/summary.json").is_file()]
    run_rows = [audit_run(path) for path in runs]
    inst_current = sha256(INST_CONCLUSION)
    rel = "experiments/results/EXP-INST-001/conclusion.json"
    baseline_rev, inst_baseline = None, None
    for rev in INST_BASELINE_REVS:
        inst_baseline = git_blob_hash(rev, rel)
        if inst_baseline is not None:
            baseline_rev = rev
            break
    ok = inst_baseline is not None and bool(run_rows) and all(
        row["status"] == "INSTRUMENT_INCOMPLETE"
        and row["cells"] == row["expected_cells"] == 72
        and row["complete_delays"] == []
        and row["provenance_mismatches"] == []
        and row["forbidden_metric_rows"] == []
        for row in run_rows
    ) and inst_current == inst_baseline
    return {
        "status": "PASS_PROVENANCE_AUDIT" if ok else "FAIL",
        "runs": run_rows,
        "inst_conclusion_sha256_current": inst_current,
        "inst_conclusion_baseline_rev": baseline_rev,
        "inst_conclusion_sha256_baseline": inst_baseline,
        "inst_conclusion_unchanged": inst_current == inst_baseline,
        "read_only": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
