# MOTIF-FUNC-005 — block-preserving magnitude-placement control

## Status

This protocol is frozen before metrics. It is a functional readout control,
not a biological simulation, profitability result, or ML-transfer claim.

## Question

With topology and signs fixed, does the M3 routing-margin difference remain
when nonzero absolute weights are permuted only within each
source-superclass to destination-superclass block?

## Arms and controls

Reuse the exact ROUTING-003 task, fixed inputs/probes, LIF parameters, target
rate 0.013 ±15%, independent per-arm/seed calibration, train/test split,
liveness gates, positive control, 12 seeds, and 20 trials per pattern.
Smoke uses the existing smoke trial count and is not evidence.

OBSERVED uses the frozen signed weights on fixed edge coordinates.
BLOCK_MAGNITUDE_PERMUTED keeps every edge coordinate, every zero position, and
the sign at every nonzero edge fixed. Within each source-label to
destination-label block it permutes the absolute magnitudes among nonzero
edges. It therefore preserves topology, node degrees, edge count, blocks,
reciprocity, each block's sign multiset, and each block's absolute-weight
multiset; only within-block magnitude placement changes. The selected
subgraph has 23,708 records before removal of 4 source self-loops and 23,704
analyzed records.

The primary comparison is paired observed-minus-block-magnitude-permuted
routing margin over seeds where both arms are measured and alive. Claim-ready
direction requires positive control 12/12, at least 8 paired seeds, and a 95%
t interval excluding zero. Missing calibration/liveness is MISSING, never a
negative. No test tuning, post-hoc target, or p-value search.

## Interpretation

A positive result would show dependence on within-block magnitude placement
beyond preserved sign and magnitude composition. A null result would leave
the M3 effect compatible with sign placement or other within-block structure
under this control. Neither result establishes a motif, biological function,
novelty, or ML transfer.

## Compute and failure gate

Reuse the imported ROUTING-003 gain calibration bounds, including its fixed
upper cap GAIN_HI = 80.0; no new gain tuning is introduced. Smoke, then sizing,
then full, in one process at a time. Full execution is allowed only if sizing
is within the campaign's approximately four-hour cost gate and shows no RAM
risk on the 15 GiB host. If calibration or train/test liveness fails for an
arm/seed, record MISSING; never interpret it as a negative. If the cost gate
is exceeded, keep the checkpoint and classify operationally.

## Reproducibility

Write immutable checkpoints under
research/results/MOTIF-FUNC-005/FULL_<timestamp>_<gitsha>. Never touch
data/raw/ or the protected derived graph.
