# EXP-E1-MATCH — report (last comparison in the E1 lineage)

Protocol: [`experiments/results/EXP-E1-MATCH/protocol.md`](../experiments/results/EXP-E1-MATCH/protocol.md),
pushed as `fa5dd23` (2026-10-08 14:27:46 UTC); slice A started 14:27:54 UTC, slice B after it.

Change from EXP-E1-DALE: per-seed rate matching on all 210 training trials with a ±5%
bisection stop, instead of a 20-trial subsample with a ±15% stop. Arms: connectome,
Dale-preserving degree null (20 draws), Erdős–Rényi (20 draws). Cell `per_seed / full`.

## Slice A (E1 slice, seeds 4000–4023)

Artifact: `experiments/results/EXP-E1-MATCH/e1_op_match-sliceA_20261008T142754Z_fa5dd23.json`.
Complete: 24/24 connectome seeds valid.

| comparison | mean | 95% CI | n |
|---|---|---|---|
| **connectome − Dale-preserving null** | **+0.004** | **[−0.014, +0.022]** | 24 |
| connectome − Erdős–Rényi | +0.080 | [+0.060, +0.099] | 24 |

Arm means: connectome 0.862, Dale null 0.858, ER 0.782; input only 0.828.
`probe48` cell: connectome − Dale +0.005 [−0.063, +0.072] (n = 23).

Classification: **no detectable difference** between the connectome and its Dale-preserving
rewiring on slice A.

## Slice B (ranks 501–1000, seeds 5000–5023)

Artifact: `experiments/results/EXP-E1-MATCH/e1_op_match-sliceB_20261008T150424Z_ded85d8.json`
(the `ded85d8` in the name is HEAD at start; the runner file is unchanged since `fa5dd23` —
only README and demo commits came in between — and its SHA-256 is in `provenance`).
Complete: 23/24 connectome seeds valid (seed 5016 at 0.78× of target, alive). All 480 null
draw-cells of each null were in band.

| comparison | mean | 95% CI | n |
|---|---|---|---|
| **connectome − Dale-preserving null** | **−0.116** | **[−0.163, −0.069]** | 23 |
| connectome − Erdős–Rényi | −0.051 | [−0.098, −0.004] | 23 |
| connectome − input only | −0.092 | [−0.138, −0.045] | 23 |

Arm means: connectome 0.747, Dale null 0.864, ER 0.797; input only 0.839. 18 of 23 seeds
favour the Dale null. `probe48` cell: connectome − Dale −0.182 [−0.259, −0.105] (n = 23).

Classification: **connectome worse than its Dale-preserving rewiring** on slice B.

## Exploratory (post hoc, not preregistered): why +0.028 became +0.004 on slice A

The only change between EXP-E1-DALE and slice A here is the rate matcher. Ratio of the
connectome's full-set firing rate to the mean rate of its seed's valid Dale-null draws:

| run | matcher | median rate ratio (IQR) | connectome − Dale | Spearman(ratio, acc diff) |
|---|---|---|---|---|
| EXP-E1-DALE | 20-trial subset, ±15% | 1.046 (0.980–1.059) | +0.028 | +0.18 (p = 0.42, n = 22) |
| EXP-E1-MATCH A | 210 training trials, ±5% | 1.006 (0.992–1.023) | +0.004 | +0.01 (p = 0.97, n = 24) |

Under the looser matcher the connectome ran about 5% hotter than its Dale null. A residual
activity advantage is a plausible contributor to the earlier +0.028; the per-seed correlation
is weak, so this is not established. Either way, the tighter instrument does not reproduce it.

## Headline (preregistered rule)

Slice A complete, no detectable difference; slice B complete, connectome worse. Neither
complete slice shows the connectome ahead of its Dale-preserving rewiring, so the headline is:

> **Not supported.** With the instrument fixes in place, there is no evidence on either slice
> that the connectome's specific wiring carries the E1 signal better than a rewiring that keeps
> every neuron's degrees, outgoing weights and sign.

The connectome's advantage over Erdős–Rényi graphs is also slice-dependent: +0.080 on slice A
(consistent with EXP-E1-OP and EXP-E1-DALE), −0.051 on slice B.

As committed in the protocol, this closes the E1 lineage. The EXP-E1-DALE result
(+0.028 on slice A) stands as measured but is superseded: it did not reproduce under the
tighter matcher on fresh seeds of the same slice.

## What would be worth testing next (not in this repository)

- A task that needs recurrent memory (the no-network baseline is already at 0.83 here).
- Slices chosen by anatomy (a whole neuropil or circuit) rather than by degree rank.
- A null preserving both in- and out-strength (weighted configuration model), and per-seed
  readout dimensionality as a mediator.
