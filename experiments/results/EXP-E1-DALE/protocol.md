# EXP-E1-DALE — Is the degree-null "win" an artifact of breaking Dale's law?

Status: **preregistered**. Committed and pushed before any seed in this protocol is run.

## Why

EXP-E1-OP found connectome − degree-preserving null = −0.036 [−0.057, −0.016] (24 seeds).
While writing that up, a check of the null itself (2026-10-08) showed that
`flylab.nulls.degree_preserving_null` does **not** keep each neuron's outgoing weights, as its
comment claimed. In the double-edge swap (a→b),(c→d) → (a→d),(c→b) the weight permutation
travels with the *target*, so each neuron keeps its incoming weights and its outputs inherit
other neurons' signs. On the E1 slice, 479 of 500 presynaptic neurons in a null draw have both
excitatory and inhibitory outputs; in the connectome, 0 do (signs are assigned per
presynaptic neuron by transmitter, i.e. Dale's law holds by construction).

So the degree-preserving null that beat the connectome differs from it in two ways:
the wiring pattern, **and** a biologically impossible mixing of output signs. This experiment
separates them.

`degree_preserving_null(..., weights_follow="pre")` now keeps outgoing weights (and so sign
and out-strength) with the presynaptic neuron. The legacy behaviour is unchanged and remains
the default so every earlier result reproduces (`tests/test_nulls.py::test_dale_null_keeps_presynaptic_sign_and_out_strength`).

## Design

Runner: `experiments/harness/e1_operating_point.py --matchings per_seed --dale`.

Same task, slice, LIF parameters, target rate (0.002, ±15%), 60 trials/class, ridge
selection, input-only baseline and validity rules as EXP-E1-OP. Per-seed gain matching only.
Both readouts are recorded; `full` is primary.

Arms, 20 draws per null:

| arm | edges | weights |
|---|---|---|
| connectome | real | real |
| `degree_preserving_null` (legacy) | swap stream (90000, d) | follow postsynaptic neuron (breaks Dale) |
| `dale_preserving_null` | **identical edge set to the legacy draw d** | follow presynaptic neuron (keeps Dale, out-strength) |
| `er_null` | Erdős–Rényi, stream (90001, d) | uniform 1–10, random sign |

The legacy and Dale nulls share every rewired edge; they differ only in which endpoint keeps
its weight. That makes the legacy − Dale contrast a clean test of the sign-mixing effect.

Seeds: **2000–2023 (24 seeds)**, never used by any experiment.

## Endpoints (cell `per_seed / full`)

Primary: **connectome − Dale-preserving null**, paired by seed (null = mean over valid draws),
mean and two-sided 95% t-interval.

- lower bound > 0 → connectome beats its Dale-preserving rewiring
- upper bound < 0 → connectome is worse than its Dale-preserving rewiring
- otherwise → no detectable difference at n = 24

Key secondary: **legacy null − Dale null**, paired by seed, same interval. A positive interval
means the legacy null's advantage was (at least partly) produced by breaking Dale's law.

Also reported: connectome − legacy null (replication of the EXP-E1-OP primary on new seeds),
connectome − ER, connectome − input-only, and the `probe48` cell.

Exclusion rules and the > 6/24 `INSTRUMENT_INCOMPLETE` rule are those of EXP-E1-OP.

## Not a prediction

No direction is predicted for either endpoint.
