# EXP-E1-REPL — Does the Dale-null result replicate on different neurons?

Status: **preregistered**. Committed and pushed before any seed in this protocol is run.

## Why

EXP-E1-DALE found connectome − Dale-preserving degree null = +0.028 [+0.008, +0.049] on the
E1 slice (the 500 highest out-degree neurons). It was the third preregistered comparison in a
sequence, each prompted by auditing the one before, so its own report names replication on
another slice as the next step. This is that step, with nothing else changed.

## Slice B

`data/e1_slice/slice_b_rank501_1000.npz`: the neurons ranked **501–1000** by out-degree in the
full traced MaleCNS graph. **Disjoint** from the E1 slice (tested). 10,791 connections
(E1 slice: 23,708); edge signs E 3,303 / I 4,441 / zero 3,047 (28% zeroed vs 60%); neuron
signs I 248 / E 121 / unknown 131; superclasses led by central-brain intrinsic (161),
optic-lobe intrinsic (133) and descending neurons (70).

Accuracy-blind feasibility check (done before this file, no readout trained, task seeds 0–1
only): per-seed gain matching converged for the connectome and one draw of each null, with
full-trial-set rates 0.84×–1.12× of target. Connectome gains were 1.4–1.6 (E1 slice: ~12).

## Design

```
python experiments/harness/e1_operating_point.py --seeds 3000:3024 --matchings per_seed --dale \
  --slice-file data/e1_slice/slice_b_rank501_1000.npz --out-dir experiments/results/EXP-E1-REPL \
  --label repl-confirmatory
```

Everything else identical to EXP-E1-DALE: task, LIF parameters, 60 trials/class, target rate
0.002 ± 15%, ridge selection, 20 draws per null (legacy degree null, Dale-preserving degree
null on the same swap stream, Erdős–Rényi), input-only baseline, validity rules.

Seeds: **3000–3023**, never used.

## Endpoints (cell `per_seed / full`)

Primary: **connectome − Dale-preserving null**, paired by seed, mean and two-sided 95%
t-interval. Lower bound > 0 → replicates; upper bound < 0 → reverses; otherwise → does not
replicate at n = 24 (not evidence of absence).

Secondary: legacy null − Dale null; connectome − legacy null; connectome − ER;
connectome − input-only; the `probe48` cell.

More than 6 of 24 connectome seeds excluded → `INSTRUMENT_INCOMPLETE`, no direction claimed.

No direction is predicted.
