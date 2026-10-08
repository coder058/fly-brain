# EXP-E1-REPL — report

Protocol: [`experiments/results/EXP-E1-REPL/protocol.md`](../experiments/results/EXP-E1-REPL/protocol.md),
pushed as `9890393` (2026-10-08 14:12:31 UTC); run started 14:12:34 UTC.
Artifact: `experiments/results/EXP-E1-REPL/e1_op_repl-confirmatory_20261008T141234Z_9890393.json`.

## Outcome: `INSTRUMENT_INCOMPLETE` — the replication did not succeed

Only **13 of 24** connectome seeds passed the validity rules on slice B (limit: 18). Under the
preregistered rule no direction is claimed. The EXP-E1-DALE result is therefore **not
replicated** on a second slice.

For transparency, the 13 valid seeds (cell `per_seed / full`) point the **other way**:

| comparison | mean | 95% CI | n |
|---|---|---|---|
| connectome − Dale-preserving null | −0.061 | [−0.114, −0.008] | 13 |
| connectome − legacy degree null | −0.085 | [−0.138, −0.031] | 13 |
| connectome − Erdős–Rényi | +0.013 | [−0.039, +0.064] | 13 |

Arm means: connectome 0.803 (n=13), Dale null 0.866, legacy null 0.885, ER 0.792; input only
0.840. These numbers are not a result: the 11 missing seeds were not missing at random (see
below), so the valid subset may be a biased sample of the connectome's behaviour.

## Why seeds were lost

All 24 connectome cells were alive. All 11 exclusions were rate-band failures: the gain
bisection matches firing rate on a 20-trial subsample (every 15th trial), and on slice B the
connectome's rate on the full 300 trials then landed at **0.69×–4.43×** of target (seed 3018:
4.43×; bisection reported "converged" on 23/24 seeds). Null draws were in band 458–460 of 480.
The same subsample procedure worked on the E1 slice (22–24/24 in band), so the failure is
specific to a graph whose activity varies much more from trial to trial.

This is the fifth instrument limitation in this lineage that falls harder on the connectome
than on random graphs (after global gain, sparse probes, the duplicate-merging shuffle and
the Dale-violating null).

> Follow-up: [EXP-E1-MATCH](EXP_E1_MATCH.md) fixed the matcher; slice B then lost 1/24 seeds
> and the connectome was worse than its Dale-preserving rewiring (−0.116 [−0.163, −0.069]).

## What this changes

- The EXP-E1-DALE claim stays scoped to the E1 slice. It should not be described as a general
  property of fly wiring.
- The obvious instrument fix — matching each graph's rate on all training trials instead of a
  20-trial subsample — is accuracy-blind and would be tested under a new ID with new seeds.
