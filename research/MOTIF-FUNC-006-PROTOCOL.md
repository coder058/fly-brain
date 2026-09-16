# MOTIF-FUNC-006 — one-time lower operating-point magnitude replication

## Status

This protocol is frozen before metrics. It is a one-time instrument repair for
the M5 magnitude-placement contrast, not a new biological claim or an
invitation to tune targets indefinitely.

## Question

At a fixed lower operating point selected from the M5 calibration envelope,
can the observed and block-magnitude-permuted arms be compared with at least
the preregistered paired-seed power?

## Arms and controls

Reuse the exact M5 task, fixed topology, inputs/probes, LIF parameters,
block-preserving magnitude permutation, train/test split, liveness gates,
positive control, 12 seeds, and 20 trials per pattern. The only task-level
change is the preregistered target rate 0.003 ±15%, selected before M6 task
metrics from M5's observed magnitude-arm calibration outputs: M5 seed 3
reported 0.00297142094017094 at its failed target calibration. The lower target
is not biologically calibrated and is used only to test whether missingness is
operating-point limited.

The observed arm keeps frozen signed weights. The block-magnitude-permuted arm
keeps topology, zeros, signs, blocks, and block absolute-weight multisets
fixed while permuting magnitudes within blocks. Calibrate independently per
arm and seed. Missing calibration or liveness is MISSING, never a negative.

The primary comparison is paired observed-minus-block-magnitude-permuted
routing margin over seeds where both arms are measured and alive. Claim-ready
direction requires positive control 12/12, at least 8 paired seeds, and a 95%
t interval excluding zero. No test tuning, post-hoc target changes, or p-value
search. This is the single planned operating-point replication for M5; if it
does not reach the gate, close the magnitude branch rather than tuning again.

## Compute and failure gate

The target, 12 seeds, 20 trials per pattern, and imported gain cap GAIN_HI =
80.0 are fixed. Smoke, sizing, then full, one process at a time. Full
execution requires sizing within the campaign's approximately four-hour cost
gate and no RAM risk on the 15 GiB host. Preserve every seed checkpoint and
report all missing rows.

## Interpretation

A passed gate would make the M5 magnitude-placement signal measurable at this
new operating point, but would still be a locked-readout result only. Failure
or insufficient pairs means the instrument remains unresolved; neither outcome
is a claim about biology or general topology.

## Reproducibility

Write immutable checkpoints under
research/results/MOTIF-FUNC-006/FULL_<timestamp>_<gitsha>. Never touch
data/raw/ or the protected derived graph.
