# EXP-E1-OP — Does the E1 negative survive fixing two operating-point artifacts?

Status: **preregistered**. This file is committed before the confirmatory run and before any
confirmatory seed has been simulated. The commit that adds it is the timestamp of record.

## Why this experiment exists

The powered E1 result (`experiments/results/e1_null_ensemble_powered_20260915T130422Z_fe089d3.json`)
reported that the MaleCNS connectome does not beat rate-matched nulls:
connectome 0.634 ± 0.122 vs degree-preserving null 0.685 ± 0.030 (12 seeds).

A post-hoc audit of that file (2026-10-08, on a graph rebuilt from the raw Janelia files that
reproduces 165,122 neurons / 25,563,197 edges / 124,025,046 synapses exactly) found:

- The connectome scored 0.67–0.82 on 10 of 12 seeds and **chance (0.20, 0.21) on seeds 9 and 5**.
  Those two seeds account for the negative mean and the 7× wider interval.
- **Seed 9 — global rate matching.** `null_ensemble.py` matches each graph's gain once on task
  seed 0's drive, citing "drive statistics are identical across seeds by construction". They are
  not: each seed drives a different random 10% of neurons. At the matched gain the connectome's
  non-input firing rate across seeds 0–11 ranges from 0.01× to 1.97× the 0.002 target; seed 9
  is at 0.01× (306 non-input spikes vs ~15,000 for the nulls).
- **Seed 5 — sparse probe readout.** Features come from 48 fixed random non-input neurons. The
  connectome's activity is concentrated: on seed 5 it fired 20,231 non-input spikes, of which
  18 landed on the probes, and the readout was at chance on its own training set. The liveness
  guard counts pool spikes, not probe spikes, so it passed.

Both artifacts penalise a heterogeneous graph more than a homogeneous random one. Whether the
negative survives once they are removed is an open question; this experiment answers it on
seeds that have never been run.

A smoke run on the already-seen seed 0 also showed that an **input-only readout with no
reservoir** (mean drive over input neurons in the same 4 time bins) scores 0.811, above the
connectome's 0.789. That baseline is therefore part of the preregistered report.

## Design

Runner: `experiments/harness/e1_operating_point.py` (unit-tested in `tests/test_e1_operating_point.py`;
the `global/probe48` cell is tested to be bit-identical to the original harness).

Everything not listed here is unchanged from the powered E1 run: 500-node top-out-degree
subgraph, signed weights under the `glutamate_unknown` policy, LIF parameters from
`e1_config.json`, 5 classes × 60 trials, 70/30 within-class split, ridge chosen on a validation
split of train only, 20 degree-preserving null draws (RNG stream 90000, 5 swaps/edge) and 20 ER
draws (stream 90001), target non-input rate 0.002.

Factors (full 2×2, every arm and every draw):

| factor | levels |
|---|---|
| gain matching | `global` (once per graph on task seed 0, as originally) · `per_seed` (on each seed's own drive) |
| readout | `probe48` (48 fixed non-input probes, as originally) · `full` (all non-input neurons) |

Baseline: `input_only` ridge readout on the drive itself, 4 time bins.

Seeds:
- **Confirmatory: task seeds 1000–1023 (24 seeds).** Never used by any E1 run.
- Diagnostic: task seeds 0–11, already seen. Reported, never pooled with confirmatory seeds.

## Validity rules (fixed now)

A cell is valid if `check_alive` passes (unchanged guard). For `per_seed` matching a cell must
also have its measured non-input rate within ±15% of target. A seed enters a comparison only if
its connectome cell is valid and at least one null draw for that seed is valid; the null value
for a seed is the mean over its valid draws. Excluded seeds are listed with their reason.
If more than 6 of 24 confirmatory seeds are excluded from the primary cell, the primary result
is reported as `INSTRUMENT_INCOMPLETE` and no direction is claimed.

## Primary endpoint

Cell `per_seed / full`, confirmatory seeds: paired difference
**connectome − degree-preserving null**, mean with two-sided 95% t-interval.

- Lower bound > 0 → "connectome beats the degree-preserving null under this task and operating point".
- Upper bound < 0 → "connectome is worse than the degree-preserving null".
- Otherwise → "no detectable difference at n = 24".

## Secondary (reported, not used for the headline)

- Same comparison vs ER null in `per_seed / full`.
- All four cells, both nulls, confirmatory and diagnostic seeds.
- Connectome vs `input_only`, paired, in `per_seed / full`.
- Per-seed connectome rate and probe-spike counts in every cell.

## Mechanistic predictions (stated before the run)

1. In `global` cells the connectome's rate will miss the ±15% band on a substantial share of
   seeds; in `per_seed` cells it will be within the band on ≥ 90% of seeds.
2. In `probe48` cells some connectome seeds will have near-zero probe spikes despite an active
   pool; `full` removes that failure mode.

No prediction is made about the sign of the primary endpoint.

## What this cannot show

It is one task, one 500-node slice (0.3% of the CNS, hub-selected), one neuron model. A positive
primary result would be about this operating point and this readout, not about fly intelligence.
If `input_only` matches or beats every reservoir arm, the honest reading is that this task does
not need recurrent computation, and the topology comparison is about which graph degrades the
signal least.
