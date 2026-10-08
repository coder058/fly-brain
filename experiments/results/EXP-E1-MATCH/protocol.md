# EXP-E1-MATCH — Dale-null comparison on both slices with train-set rate matching

Status: **preregistered**. Committed and pushed before any seed in this protocol is run.

**This is the last comparison in the E1 lineage.** Whatever it shows, the README reports it as
the current answer; no further rerun of this question will be made in this repository.

## Why

EXP-E1-REPL (slice B) ended `INSTRUMENT_INCOMPLETE`: 11 of 24 connectome seeds failed the
±15% rate band because gain was matched on a 20-trial subsample with a ±15% stopping rule, and
the connectome's activity on slice B varies more from trial to trial than the nulls'.

Accuracy-blind feasibility check (rates only, task seeds 0–7, no readout trained), connectome
only, full 300-trial rate after matching:

| slice | 20-trial subset, stop at ±15% | all training trials, stop at ±5% |
|---|---|---|
| E1 slice | 8/8 in band | 8/8 in band |
| slice B | 4/8 in band (1.15–1.67× out) | 7/8 in band (seed 3 at 1.34×) |

## Design

Matching: per seed, on **all training trials** (210; test trials are never used), bisection
stops at ±5%. Validity band unchanged: full-set non-input rate within ±15% of 0.002.

Arms: connectome, **Dale-preserving degree null** (20 draws, swap stream (90000, d),
`weights_follow="pre"`), Erdős–Rényi (20 draws). The legacy sign-mixing null is dropped to
halve the cost; its effect was measured in EXP-E1-DALE (+0.048, 24/24 seeds). Readouts:
`probe48` and `full`; `full` is primary. Everything else as in EXP-E1-DALE.

```
# slice A (E1 slice), seeds 4000-4023
python experiments/harness/e1_operating_point.py --seeds 4000:4024 --matchings per_seed --dale \
  --arms dale_preserving_null,er_null --match-on train --match-tol 0.05 \
  --out-dir experiments/results/EXP-E1-MATCH --label match-sliceA
# slice B (ranks 501-1000), seeds 5000-5023
python experiments/harness/e1_operating_point.py --seeds 5000:5024 --matchings per_seed --dale \
  --arms dale_preserving_null,er_null --match-on train --match-tol 0.05 \
  --slice-file data/e1_slice/slice_b_rank501_1000.npz \
  --out-dir experiments/results/EXP-E1-MATCH --label match-sliceB
```

Seeds 4000–4023 and 5000–5023 have never been used.

## Endpoints (cell `per_seed / full`)

Primary, evaluated **separately for each slice**: connectome − Dale-preserving null, paired by
seed, mean and two-sided 95% t-interval, with the usual rule (lower > 0 → connectome better;
upper < 0 → worse; else no detectable difference) and `INSTRUMENT_INCOMPLETE` if more than 6
of 24 connectome seeds are excluded.

Headline rule, fixed now:

- **"Replicates across slices"** only if both slices are complete and both lower bounds > 0.
- **"Slice-dependent"** if the two complete slices disagree in classification.
- **"Not supported"** if neither complete slice shows the connectome ahead.
- If either slice is `INSTRUMENT_INCOMPLETE`, the headline says so and makes no cross-slice claim.

Secondary: connectome − ER and connectome − input-only per slice; `probe48` cells; per-seed
rate distribution of every arm.

No direction is predicted.
