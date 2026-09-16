# EXP-INST-001 protocol (locked before the run)

**ID:** EXP-INST-001  
**Kind:** instrument validation, not a topology test. PASS and FAIL are both valid.  
**Question:** At the original E1 measurement config, can the instrument detect an accuracy effect of ~0.15?

## Verified E1 measurement config

From `experiments/results/e1_null_ensemble_powered_20260915T130422Z_fe089d3.json` `settings`:

| Knob | Value |
|---|---|
| n_probes | 48 |
| target_rate | 0.002 |
| polarity | signed (`connectome_signed`) |
| n_seeds | 12 (seeds 0–11) |
| n_trials_per_class | 60 |
| subgraph | top-500 out-degree |
| n_steps | 64 |
| n_classes | 5 |
| split | per-class first 70% train / last 30% test, no shuffle |
| classifier | `ridge_sweep` (ridge chosen on train-only val split) |
| metric | held-out accuracy |
| gain match | once on seed 0 (E1 runner) |

`e1_config.json` does **not** set `n_probes` or `target_rate`. Its `n_trials_per_class=20` and 5 seeds are the pilot defaults; the powered E1 run overrode them via CLI. `e1_reservoir.simulate_driven` defaults `n_probes=48`. PROTOCOL.md requires 12×60 for structure comparisons. These layers **agree** on the measurement config above; they are not a silent conflict.

Gate vs target: `positive_control.MIN_EFFECT = 0.10` is the detection threshold. PROTOCOL's "real 0.15 effect" is the effect size this experiment injects. Not a conflict: inject 0.15, pass only if the estimate satisfies the pre-existing 0.10 + CI-excludes-0 rule. Do not lower 0.10.

## Why stock PC-A / PC-B are not this experiment

1. **Unknown true effect.** PC-B is ring vs ER. The accuracy gap at 48 / 0.002 is not 0.15 by construction. A fail cannot distinguish "instrument cannot see 0.15" from "ring–ER gap at this operating point is ≪ 0.15".
2. **Wrong polarity.** Stock PC-B is all-excitatory. E1 was signed / inhibition-dominated.
3. **Wrong graphs.** Ring and ER are not the signed E1 connectome instrument.
4. **Wrong classifier.** Stock PC uses `fit_readout(..., ridge=10)`, not E1's `ridge_sweep`.
5. **No zero-effect control.** PC-B has no label-shuffled / no-signal arm, so it cannot measure false positives.
6. **PC-A is a large activity contrast** (historical Δacc ≈ 0.53–0.58), not a 0.15 effect.

Stock PC-B is therefore scientifically invalid for the question asked. EXP-INST-001 replaces it with a constructed-effect control on the **same** E1 pipeline. Stock PC-B is not re-run. EXP-006 is not reopened.

## Constructed positive control (locked)

- Same signed connectome, 48 probes, target_rate 0.002, 12×60, same split, same `ridge_sweep`, same metric.
- After reservoir features `X` are computed, add a class-conditional template of locked amplitude. The readout is not told which condition it is scoring.
- Amplitude `alpha_star` is calibrated on **isotropic Gaussian N(0,1)** features of the same shape (N trials × D features), never on reservoir data, so that mean paired Δacc (true-label injection vs label-shuffled injection) ≈ 0.15.
- Unit conversion onto spike-bin features is the Bernoulli bin-mean std implied by the registered E1 operating point, **not** empirical train std:
  `sigma_theory = sqrt(target_rate * (1-target_rate) / (n_steps/n_bins))`.
  Real injection: `X + (alpha_star * sigma_theory) * templates[y]`.
  Smoke found that mean per-feature train std on sparse 48-probe rasters is dominated by silent coordinates and made the injection a no-op (Δacc=0). That is a unit-conversion bug, not a retune of the 0.15 target. `alpha_star` is not retuned after seeing reservoir accuracies. Empirical `sigma_train` is recorded only as a diagnostic.
- **Null / FP control:** same energy, labels shuffled (`n_null_perms=20` independent permutations). The instrument must not pass the gate on a no-association contrast.
- **No-injection arm:** `X` as-is, for baseline accuracy only.

## Gate (predefined, not weakened)

Reuse `positive_control.verdict` / `MIN_EFFECT=0.10`:

`INSTRUMENT_VALID_E1 = TRUE` iff the 12-seed paired contrast  
**(true-label injection) − (one locked shuffled injection)**  
has `|mean_diff| ≥ 0.10` **and** 95% CI excludes 0.

Primary mean excludes seeds that fail `check_alive`. If fewer than 12 live seeds remain, the gate is not passed (power floor not met). Dead seeds are recorded, not silently averaged.

A failed gate means: **this E1 config lacks sensitivity to detect the predefined effect.** It does not mean the connectome topology is false, and it does not mean Fly "doesn't work."

## What is not changed after seeing data

Firing rate, probe count, signed vs all-excitatory, graph, classifier, metric, split, null construction, randomization streams, `alpha_star`, `MIN_EFFECT`.

## Residual

Injection sits on reservoir features (after LIF, before readout). It tests whether **this measurement procedure** (48-probe sparse features at rate 0.002 + ridge + 12×60 paired CI) can detect a 0.15 accuracy effect in that noise. It does not inject a topological difference into the graph.
