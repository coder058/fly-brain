# EXP-E1-OP — report

Protocol: [`experiments/results/EXP-E1-OP/protocol.md`](../experiments/results/EXP-E1-OP/protocol.md),
committed and pushed as `214c7c7` (2026-10-08 13:11 UTC) before any confirmatory seed ran.
Runner: [`experiments/harness/e1_operating_point.py`](../experiments/harness/e1_operating_point.py).

## Outcome

**Primary (per-seed gain, full readout, seeds 1000–1023):**
connectome − degree-preserving null = **−0.036, 95% CI [−0.057, −0.016]**, n = 24, no exclusions.
Under the preregistered rule: *the connectome is worse than the degree-preserving null under
this task and operating point.* 19 of 24 seeds point the same way.

`E1_TOPOLOGY_ADVANTAGE` remains CLOSED. This is a new ID, not a rerun of the closed one,
and it reaches the same direction with an interval ~5× narrower (≈4× from lower seed-to-seed
variance of the paired difference, ≈1.4× from doubling the seeds).

## Confirmatory table

Accuracy, 5 classes (chance 0.20). Null columns average 20 draws per seed. `n` < 24 means
connectome cells refused by the liveness guard.

| matching / readout | connectome | DP null | ER null | conn − DP | conn − ER |
|---|---|---|---|---|---|
| global / probe48 (original) | 0.754 (n=20) | 0.719 | 0.650 | +0.042 [−0.041, +0.126] | +0.102 [+0.024, +0.180] |
| global / full | 0.877 | 0.892 | 0.785 | −0.015 [−0.037, +0.007] | +0.092 [+0.068, +0.116] |
| per_seed / probe48 | 0.712 (n=21) | 0.739 | 0.656 | −0.024 [−0.093, +0.044] | +0.055 [−0.009, +0.118] |
| **per_seed / full** | **0.869** | **0.906** | **0.788** | **−0.036 [−0.057, −0.016]** | **+0.081 [+0.063, +0.100]** |

Input-only baseline (no network): 0.830. Connectome − input-only, paired:
per_seed/full **+0.039 [+0.016, +0.063]**; per_seed/probe48 **−0.117 [−0.184, −0.051]**.

## Preregistered mechanistic predictions

| prediction | observed | held? |
|---|---|---|
| Global gain leaves the connectome off the ±15% rate band on a substantial share of seeds; per-seed matching puts ≥ 90% in band | global: **4/24** in band, rate 0.10×–3.32× of target; per-seed: **24/24** in band (0.85×–1.15×) | yes |
| 48-probe readout produces near-zero probe activity despite an active pool; full readout removes it | probe48 refusals on seeds 1001, 1004, 1008, 1018: 11,870–18,306 pool spikes, 6–198 probe spikes; full readout: **0** refusals | yes |

Nulls under per-seed matching: 468/480 DP and 450/480 ER draw-cells in band; out-of-band draws
were excluded per protocol (each seed kept ≥ 1 valid draw of each null).

## Interpretation

1. **Per-neuron statistics, not wiring.** The connectome beats an Erdős–Rényi graph with the
   same number of edges by 8 points, and loses by 3.6 points to a rewiring of itself that
   keeps every neuron's in/out-degree and outgoing weights and sign. The particular pattern of
   who-connects-to-whom is, if anything, slightly harmful for this task. The ER null differs
   from the connectome in degrees, weight distribution (uniform 1–10 vs synapse counts with
   60% zeroed) *and* sign structure, so this experiment does not say which of those carries
   the advantage over ER; a weight-permutation and a sign-shuffle null would.
2. **The original instrument hid a usable network.** With the 48-probe readout the connectome
   was 0.117 *below* reading the input directly. With a full readout it is 0.039 above. The
   E1 reservoir only becomes a computer at all once you look at the neurons doing the work.
3. **The old negative was right for the wrong reasons.** Its direction survives; its width
   came from the two artifacts, which hit the connectome harder than either null.

Hypotheses for why the real wiring trails its degree-matched null (not tested here): the swap
null destroys reciprocity, clustering and the 4 autapses, which may concentrate activity onto
fewer neurons in the real graph and reduce the readout's effective dimensionality.

## Provenance notes

- Erratum to the protocol text: it says the connectome scored "0.67–0.82 on 10 of 12 seeds";
  seed 11 scored 0.511, so the range is 0.51–0.82. The protocol file is left as committed.

- The confirmatory JSON's `provenance.git_rev` reads `fe40667`. The run **executed** the
  runner at `214c7c7`: `provenance()` reads `HEAD` when the result is written, and
  `fe40667` was committed while the 17-minute run was in flight. The only code difference
  between the two commits is the graph loader (bundled slice vs extraction from the full
  graph), which `tests/test_slice.py` proves edge-identical; the in-flight run used the
  full-graph path. The file is append-only and was not renamed. The runner now captures
  provenance (including its own SHA-256) at start.
- The seed-9 anomaly was visible in September (`SCIENTIFIC_CLAIMS.md`, EXP-INST-001 residuals:
  "Seed 9 still 306 non-input spikes") but was not traced to the per-seed input draw then.

## Diagnostic run on seeds 0–11 (already seen; not pooled)

Artifact: `experiments/results/EXP-E1-OP/e1_op_diagnostic_20261008T133630Z_a4d7a97.json`.

**Bit-identical reproduction.** The `global/probe48` cell on seeds 0–11 reproduces the
September powered run exactly, from a graph rebuilt from the raw Janelia files on a different
machine: all 10 scored connectome accuracies match to every digit, and 223/223 scored
degree-preserving draws match. Seeds 5 and 9 are now refused by the current liveness guard
(the September guard only required `pool_spikes > 0`): seed 5 had 20,231 pool spikes and 18
probe spikes; seed 9 had 306 pool spikes and 0 probe spikes.

| matching / readout | connectome | DP null | ER null | conn − DP | conn − ER |
|---|---|---|---|---|---|
| global / probe48 | 0.720 (n=10) | 0.721 | 0.651 | −0.002 [−0.076, +0.072] | +0.075 [+0.007, +0.143] |
| global / full | 0.808 | 0.892 | 0.791 | −0.084 [−0.164, −0.004] | +0.017 [−0.058, +0.093] |
| per_seed / probe48 | 0.733 (n=10) | 0.728 | 0.649 | −0.001 [−0.062, +0.061] | +0.090 [+0.039, +0.142] |
| per_seed / full | 0.832 (n=11) | 0.903 | 0.790 | −0.070 [−0.107, −0.034] | +0.042 [+0.005, +0.078] |

Input-only: 0.842. In `per_seed/full`, seed 9 was excluded: its connectome rate landed at
1.166× target on the full trial set, just outside the ±15% band, although the bisection on
the matching subset had converged.

The diagnostic seeds point the same way as the confirmatory ones. They are not pooled with
them and are not evidence on their own: these seeds motivated the hypothesis.
