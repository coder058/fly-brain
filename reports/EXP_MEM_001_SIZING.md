# EXP-MEM-001 post-INST sizing — 2026-09-16

## Disposition

`INVALIDATED` as an instrument-sizing tranche; this is not evidence for or against connectome memory.

Artifact: `experiments/results/EXP-MEM-001/post_inst_20260916T030347Z_dcc995f/sizing/summary.json`

The registered sizing used seeds 100–105, six delays, 30 train/test trials per class and the five structural families. The summary reports `all_network_liveness_passed: false` and `all_primary_rate_matches_passed: false`; no pilot power estimate was produced.

Observed failures were retained in the raw cells. The random-per-seed input map produced no live calibration candidate for seeds 101, 102, 103 and 105, so those cells were recorded with null accuracy. Seed 100 had live connectome/DP calibration but `weight_perm-1` failed liveness at delays 250 and 500. Seed 104 had live calibration but isolated DP/ring failures at some delays. These are instrumentation failures, not a Fly loss and not a memory curve.

The registered accuracy-blind static routing-map repair was run once and is reported separately. Because it still failed required liveness, the loop stops scientifically as `HUMAN_STOP`; no further map or operating-point changes are authorized by this cycle.
