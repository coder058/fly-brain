# EXP-E1-DALE — report

Protocol: [`experiments/results/EXP-E1-DALE/protocol.md`](../experiments/results/EXP-E1-DALE/protocol.md),
committed and pushed as `1752800` (2026-10-08 13:45:11 UTC); the run started at
13:45:22 UTC. Artifact:
`experiments/results/EXP-E1-DALE/e1_op_dale-confirmatory_20261008T134522Z_1752800.json`
(written by the runner into `EXP-E1-OP/`, moved unchanged).

> **Superseded by [EXP-E1-MATCH](EXP_E1_MATCH.md).** On fresh slice-A seeds with a tighter
> rate matcher the primary became +0.004 [−0.014, +0.022]; on slice B, −0.116 [−0.163, −0.069].
> The sign-mixing finding below (+0.048, 24/24 seeds) is unaffected.

## The bug that motivated it

`flylab.nulls.degree_preserving_null` was documented as moving each weight "with its
presynaptic neuron". It moved it with the postsynaptic one. On the E1 slice:

| graph | neurons whose outputs are both excitatory and inhibitory |
|---|---|
| connectome | 0 of 500 (sign is per presynaptic neuron, from its transmitter) |
| legacy degree null | **479 of 500** |
| Dale-preserving degree null (`weights_follow="pre"`) | 0 of 500 |

The legacy null therefore kept each neuron's degrees and *incoming* signed weights, but gave
almost every neuron a mix of excitatory and inhibitory outputs — which no real neuron in this
model has. Every degree-null result before 2026-10-08 (E1 powered, EXP-E1-OP, and the
`research/` routing and specialization tracks, which call the same function with signed
weights) used the legacy convention. It is kept as the default so those results reproduce.

## Outcome (cell `per_seed / full`, seeds 2000–2023)

| comparison | mean | 95% CI | n | seeds in favour |
|---|---|---|---|---|
| **connectome − Dale-preserving null** *(primary)* | **+0.028** | **[+0.008, +0.049]** | 22 | 15/22 |
| **legacy null − Dale null** *(key secondary)* | **+0.048** | **[+0.038, +0.059]** | 24 | 24/24 |
| connectome − legacy null (replication of E1-OP primary) | −0.021 | [−0.045, +0.002] | 22 | |
| connectome − Erdős–Rényi | +0.101 | [+0.080, +0.123] | 22 | |
| connectome − input only | +0.051 | [+0.026, +0.075] | 22 | |

Arm means: connectome 0.882, legacy degree null 0.902, Dale degree null 0.854, ER 0.780,
input only 0.832. Two connectome seeds were excluded under the rate rule (2007 at 0.85×,
2012 at 0.75× of target, both alive); the limit was 6. Null draw-cells in band: Dale 452/480,
legacy 463/480, ER 460/480.

`probe48` cell (secondary): connectome − Dale +0.005 [−0.061, +0.072], n = 22 — the sparse
readout again cannot resolve the comparison.

Under the preregistered rule: **the connectome beats its Dale-preserving rewiring** under this
task and operating point.

## Reading

1. **Mixing output signs is worth ~5 points on this task, every time.** The legacy and Dale
   nulls share every edge; only the weight assignment differs, and the sign-mixed one wins on
   all 24 seeds. That is enough to turn a connectome advantage into an apparent deficit.
2. **With a biologically valid null, the specific wiring helps.** Holding each neuron's
   degrees, outgoing weights and sign fixed, the real who-connects-to-whom pattern beats the
   rewired one by 2.8 points (roughly a quarter of its 10-point lead over a random graph).
3. **The EXP-E1-OP primary replicates in direction** (−0.021 vs −0.036) on new seeds, but
   its interpretation changes: it measured "connectome vs a Dale-violating rewiring".

## Limits

- One task, one LIF model, one 500-neuron hub-selected slice; the effect is 2.8 points with a
  lower bound of 0.8.
- This is the third preregistered comparison in this lineage, each motivated by an audit of
  the last. Each primary was fixed before its run, but a reader should weigh the sequence, not
  the last interval alone. Replication on another slice or task is the obvious next step.
- The Dale null shuffles incoming strength; a null that preserves both in- and out-strength
  (e.g. a weighted configuration model) would be stricter still.
