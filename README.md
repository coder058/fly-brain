# Fly Brain Lab

An auditable, CPU-only research harness for asking controlled machine-learning questions of a frozen connectome.

This repository is a research testbed, not a claim that a simulation is a living fly, that biological topology automatically wins, or that any result demonstrates biological intelligence.

## Current evidence boundary

- MaleCNS v1.0 is recorded as **165,122 neurons**, **25,563,197 directed edges**, and a measured weight sum of **124,025,046** after the recorded `Traced both ends` filter.
- The source lock and derived sparse graph are preserved and verified read-only. The original raw dataset and protected graph archive are intentionally not included in this public snapshot.
- `EXP-INST-001` is a limited post-LIF feature-injection instrument result (`Δ = 0.3648` under its registered setup). It is not a topology or memory result.
- `EXP-MEM-003` is `MEM_003_NO_PAIR`: two registered maps wrote their cells, but no delay contained a live, rate-matched connectome/DP pair. No memory curve was produced.
- `EXP-GLU-001` is `COMPLETE_METRIC_WITHHELD`: all 12 checkpoints were written, but the preregistered aggregate comparison was withheld because the required validity gate was not met.
- `EXP-IGNITE-001` and `EXP-IGNITE-002` are `NO_COIGNITE`: no primary pair was found under their registered operating points. They do not establish that the connectome has no memory or that topology has no value.
- Archived `MOTIF-FUNC-003` through `006` full-run block comparisons are invalidated by a
  local/global superclass-index error. The implementation is repaired;
  corrected 12-seed runs and engineering audits are documented in the
  [erratum](reports/MOTIF_FUNC_003_006_ERRATUM.md). They are disclosed
  post-result repairs, not independent scientific confirmation.

These are instrument and operating-point outcomes. A missing or invalid liveness row is not a negative score for the connectome.

## What is implemented

- Pre-registered experiment protocols and append-only result directories
- Per-seed checkpoints with explicit liveness, rate and failure fields
- Independent train/test liveness checks and rate matching
- Sparse graph representations and structural verification
- Nonzero-synapse operations accounting
- Protected graph-build destinations
- JSON/YAML evidence records, a research ledger and a claims taxonomy
- A bounded local A2A queue prototype; it does not execute external workers
- Python tests for graph controls, leakage, determinism, liveness and queue boundaries

## What remains unfinished

- A valid connectome/DP operating point and a preregistered memory curve
- A powered comparison with controls that satisfy the validity gates
- Hardware or a reproducible simulator for navigation experiments
- A separately authorized protocol for the queued continual-learning/architecture track

The next credible result is not a larger claim. It is an operating point that survives liveness, rate matching and reproducibility.

## Reproducibility

The commands below assume that the dataset is available locally and that the environment has been installed from `requirements.txt`:

```text
.venv/bin/python scripts/verify_graph.py
.venv/bin/python scripts/verify_experiment_provenance.py
.venv/bin/python -m pytest -q
```

The verification commands do not rebuild the graph or write to `data/raw/`. The graph builder requires an explicit side-directory and rejects the protected graph destination.

## Public snapshot boundary

This repository contains source code, documentation, tests and lightweight evidence artifacts. The raw MaleCNS files and the protected derived graph archive are not redistributed here. The dataset license and source hashes are recorded in `RESEARCH_LEDGER.yaml` and `data/manifests/source.lock.json`.

Portfolio case study: https://coder058.github.io/profile/projects/fly-brain.html
