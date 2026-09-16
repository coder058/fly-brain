# MOTIF-FUNC-002 — fixed-topology signed-weight permutation control

## Status

This protocol is frozen before metrics. It is a functional readout control,
not a biological simulation, profitability result, or ML-transfer claim.

## Question

With the observed topology fixed, does global permutation of signed weights
erase the MOTIF-FUNC-001 routing-margin difference?

## Arms

Reuse the exact ROUTING-003 task, fixed inputs/probes, LIF parameters, target
rate 0.013 ±15%, independent per-arm/seed calibration, train/test split,
liveness gates, positive control, 12 seeds, and 20 trials per pattern.
Smoke uses the existing smoke trial count and is not evidence.

OBSERVED uses the 23,708 non-self-loop edge records and their frozen signed
weights, including UNKNOWN zero-weight records as topology. WEIGHT_PERMUTED
uses the identical edge coordinates and a global seed-specific permutation of
those signed weights. Therefore topology, node degrees, blocks, reciprocity,
edge count, and weight multiset are fixed; only weight placement changes.

The primary comparison is paired observed-minus-weight-permuted routing margin
over seeds where both arms are measured and alive. Claim-ready direction
requires positive control 12/12, at least 8 paired seeds, and a 95% t interval
excluding zero. Missing calibration/liveness is MISSING, never a negative. No
test tuning, post-hoc target, or p-value search.

## Interpretation

A positive result isolates a dependence on signed-weight placement for this
locked LIF task, not a motif, biological, general topology, novelty, or ML
claim. A null result says the broad M1 functional difference is not explained
by weight placement under this permutation. Either outcome leaves broader
structure and task limitations explicit.

## Compute and failure gate

Reuse the imported ROUTING-003 gain calibration bounds, including its fixed
upper cap GAIN_HI = 80.0; no new gain tuning is introduced. The smoke must
complete before sizing. Full execution is allowed only if the sizing run
estimates completion within the campaign's approximately four-hour cost gate
and does not indicate a RAM risk on the 15 GiB host. If calibration or
train/test liveness fails for an arm/seed, record MISSING; never interpret it
as a negative. If the cost gate is exceeded, stop the job with its checkpoint
and classify the run operationally, without shrinking the preregistered
science.

## Reproducibility

Smoke, sizing, then full. Run one process only. Write immutable checkpoints
under research/results/MOTIF-FUNC-002/FULL_<timestamp>_<gitsha>. Never touch
data/raw/ or the protected derived graph.


## Post-run audit correction

The frozen pre-run text described 23,708 non-self-loop records. The independent
audit found 23,708 records in the selected subgraph before removing 4 source
self-loops; the functional run therefore used 23,704 non-self-loop records,
matching its immutable metadata and runner. This wording correction does not
alter the run, checkpoints, or metrics. The pre-run protocol hash used by the
artifact is recorded in the ledger and summary.
