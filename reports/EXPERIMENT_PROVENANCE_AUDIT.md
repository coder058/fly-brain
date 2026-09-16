# Experiment provenance audit — 2026-09-16

`scripts/verify_experiment_provenance.py` performed a read-only audit of both
full MEM-002 runs and the immutable INST-001 conclusion artifact.

| Run | Cells | Calibrations | Status | Complete delays | Provenance mismatches | Forbidden metric rows |
|---|---:|---:|---|---|---:|---:|
| `q0_20260916T054112Z_d6a9572` | 72/72 | 12 | `INSTRUMENT_INCOMPLETE` | none | 0 | 0 |
| `q0_20260916T055512Z_cd028e2` | 72/72 | 12 | `INSTRUMENT_INCOMPLETE` | none | 0 | 0 |

The current `experiments/results/EXP-INST-001/conclusion.json` SHA-256 is
`64098d2e52b17fa07cb939d73bb7d32bb8ec8b36537e45c22d18fdfc36c7aff0`, exactly
matching the blob from commit `a01037d`. The audit did not modify any result.
