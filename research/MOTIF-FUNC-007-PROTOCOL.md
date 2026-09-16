# MOTIF-FUNC-007 — cross-stream-pair weight-placement replication

## Status

This protocol is frozen before metrics. It is an independent stream-pair
replication of the narrow M2 functional readout, not a biological or ML claim.

## Question

Does the observed signed-weight assignment again exceed a global signed-weight
permutation when the locked task uses a new cross-superclass stream pair?

## Arms and controls

Reuse the exact ROUTING-003 task, target rate 0.013 ±15%, LIF parameters,
calibration bounds, train/test split, liveness gates, positive control, 12
seeds, and 20 trials per pattern. The edge topology, 23,704 non-self-loop
records, and signed weights are unchanged from M2. The only task change is the
predeclared stream pair: A = cb_intrinsic and B = visual_centrifugal. Both
labels have the locked 16-input plus 32-probe capacity in the fixed 500-node
subgraph. No test or target tuning is allowed.

OBSERVED uses frozen signed weights. WEIGHT_PERMUTED uses the identical edge
coordinates and a seed-specific global permutation of signed weights. Thus
topology, node degrees, blocks, reciprocity, edge count, and weight multiset
are fixed; only weight placement changes. Calibrate each arm and seed
independently. Missing calibration/liveness is MISSING, never a negative.

The primary comparison is paired observed-minus-weight-permuted routing margin
over seeds where both arms are measured and alive. Claim-ready direction
requires positive control 12/12, at least 8 paired seeds, and a 95% t interval
excluding zero. Smoke is not evidence. No post-hoc stream, target, or test
selection.

## Interpretation

A positive result would replicate dependence on signed-weight placement for a
second stream pair under the same locked readout. A null or incomplete result
would bound generality to the earlier pair/task operating point. Neither
outcome establishes a motif, biological function, novelty, or ML transfer.

## Compute and failure gate

Use the imported ROUTING-003 gain cap GAIN_HI = 80.0. Smoke, sizing, then full,
one process at a time. Full execution is allowed only if sizing is inside the
approximately four-hour campaign cost gate and shows no RAM risk on the 15 GiB
host. Preserve all checkpoints and missing rows.

## Reproducibility

Write immutable checkpoints under
research/results/MOTIF-FUNC-007/FULL_<timestamp>_<gitsha>. Never touch
data/raw/ or the protected derived graph.
