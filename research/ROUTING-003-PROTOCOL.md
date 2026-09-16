# ROUTING-003 — operating-point replication

## Status

This protocol is frozen before any ROUTING-003 task metrics. ROUTING-003 is a
new experiment. It does not alter or rescue ROUTING-001.

## Question and hypothesis

Question: under a common operating point selected from the calibration-only
ROUTING-002 envelope, does the two-stream routing margin replicate in the
connectome relative to structural controls?

The hypothesis is two-sided. The connectome may have a positive, null, or
negative paired contrast versus the block-preserving control. A positive result
would be limited to this task and simulator.

## Operating-point selection

ROUTING-002 measured a minimum connectome maximum-grid rate of
0.012211197. The new target is fixed at TARGET_RATE = 0.013 with relative
tolerance 0.15. This target is selected after the calibration-only run, before
ROUTING-003 task metrics, by rounding the minimum connectome maximum-grid rate
upward to three decimal places. The selection uses no ROUTING-001 or
ROUTING-003 task labels, readouts, or test metrics. It is an operating-point
decision, not a biological firing-rate claim.

Each arm and seed is independently calibrated on the fixed gain range
[0.05, 80.0] with at most 24 bisection iterations. If the target is not
reachable within the frozen range and tolerance, record MISSING; do not
substitute a gain or score the task row. Calibration currents are separate
from task trials. Record native and matched rates.

## Graphs and task

Use the exact repaired ROUTING-001 500-node induced subgraph, selected labels,
local-ID input/probe partition, signed connectome, degree-preserving null, and
block-preserving null constructor. The primary contrast is
connectome_signed versus block_preserving. Degree-preserving is secondary.
Use the same two-stream balanced patterns, input pulse, membrane-voltage
features, four temporal bins, 20 trials per pattern, 14 train and 6 test per
pattern, and 12 seeds 0..11. The positive control is the same known routing
graph and must pass in all planned seeds.

No input node may be a probe. No task test label may affect gain, readout, or
stopping decisions. Ridge selection is train-only.

## Validity and gate

Check liveness independently in train and test. A row is MISSING if calibration
fails, the positive control fails, pool activity is silent, either probe stream
has no membrane-state variation, feature variance is too small, or fewer than
10 unique rows occur in either split. Retain every missing row in its seed JSON.

Primary validity requires all 12 connectome and block rows alive and accepted at
the fixed operating point. The paired primary result is the 12-seed
connectome-minus-block routing-margin contrast with a two-sided paired t 95%
CI. SUPPORTED requires: positive control passes, all primary rows are valid,
the paired mean is positive, the CI excludes zero, and connectome mean margin
is at least 0.10. Otherwise classify INCONCLUSIVE, NOT_SUPPORTED, or
INVALIDATED according to validity and CI. This gate does not establish
biology, novelty, profitability, or ML transfer.

## Compute, controls, and failure policy

Estimated arithmetic workload is inherited from ROUTING-001: 3 arms, 12 seeds,
80 task trials, 32 steps, plus calibration, readout, and positive control. This
is an estimate, not a measured runtime. Run one job only. Smoke is diagnostic
and cannot provide evidence. Perform sizing before full execution. Stop before
execution if RAM, disk, protected paths, or runtime risk becomes material.

## Reproducibility

Write one immutable seed JSON, metadata, and summary under
research/results/ROUTING-003/FULL_<timestamp>_<gitsha>. Record exact git tip,
protocol/code/graph hashes, selected nodes, labels, gains, native/matched
rates, liveness, and all gate fields. Never overwrite earlier artifacts.
