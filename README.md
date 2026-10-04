# Fly Brain Lab


An auditable, CPU-only research harness for asking controlled machine-learning questions of a frozen connectome.


This repository is a research testbed, not a claim that a simulation is a living fly, that biological topology automatically wins, or that any result demonstrates biological intelligence.


## Closed memory results (2026-10-03)

- `EXP-ANN-MB-MEM-001` is closed positive at delay 10 only (connectome 0.725 vs degree-preserving null 0.525, n=7). Delays 100 and 250 had no paired result.
- `EXP-ANN-MB-MEM-002` is closed positive. Spoken claim: connectome beats the null at delays 10 (0.706 vs 0.577, n=12) and 250 (0.621 vs 0.517, n=6). Delay 100 is a mean win only (0.600 vs 0.538, n=6) because the interval includes zero.
- This is not a full 165k dynamics result. Sensor and drone work is not a result.

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


- A tighter delay-100 result (the closed MEM-002 gap there is a mean win only)
- A powered comparison with controls that satisfy the validity gates
- Hardware or a reproducible simulator for navigation experiments
- A separately authorized protocol for the queued continual-learning/architecture track


The next credible result is not a larger claim. It is an operating point that survives liveness, rate matching and reproducibility.


## Reproducibility


The commands below assume that the dataset is available locally and that the environment has been installed from `requirements.txt`:
