# MOTIF-FUNC-001 — signed functional readout of the residual motif control

## Status

This protocol is frozen before functional metrics. It tests a computational
readout on a signed graph; it is not a biological simulation or an ML
architecture claim.

## Question

Under the locked two-stream LIF routing task, does the observed signed
topology produce a different routing margin from global degree+reciprocity
nulls?

## Arms and controls

Use the exact ROUTING-003 task, inputs, probes, seed streams, LIF parameters,
target rate 0.013 ±15%, calibration bounds, train/test split, liveness checks,
and positive control. Use 12 seeds and 20 trials per pattern; smoke is one
seed with the existing smoke trial count and is not evidence.

Arm OBSERVED uses all 23,708 non-self-loop directed edge records and their
frozen signed weights, including UNKNOWN zero-weight records as topology.
Arm NULL uses the M7B global two-edge and reciprocal-pair swaps: preserve exact
node in/out degree, edge count, and reciprocal-pair count; intentionally do not
preserve superclass blocks. Carry each edge-record weight with its swapped
unit. Calibrate gain independently per arm and seed. Missing or dead train/test
readouts are MISSING, never a negative.

The positive control must pass the ROUTING-003 margin gate in the full run.
The primary comparison is the paired routing-margin difference
OBSERVED minus NULL over seeds where both arms are measured and alive. A
claim-ready directional result requires at least 8 paired seeds and a 95%
t interval excluding zero in the predeclared direction. Otherwise classify
INCONCLUSIVE. No tuning on test, no post-hoc target, and no p-value search.

## Measurements

For every arm/seed report calibration, train/test liveness separately,
pool/probe activity, feature uniqueness, within/cross accuracies, routing
margin, edge/weight diagnostics, and exact artifact hashes. Report all
paired rows, mean, SD, 95% t interval, and missing seeds.

## Interpretation

A positive margin difference is evidence only that this locked readout
distinguishes the observed signed graph from this degree+reciprocity null.
It does not show a biological function, a topology advantage in general, or
an ML transfer benefit. A null result is a valid failure of this instrument
for this comparison.

## Compute and reproducibility

Smoke, sizing, then full. Run one process only. Write immutable checkpoints
under research/results/MOTIF-FUNC-001/FULL_<timestamp>_<gitsha>. Never touch
data/raw/ or the protected derived graph. The existing ROUTING-003 constants
are imported rather than redefined.
