# E1 audit fixes — what was broken, what changed, what it measures now

**Scope.** Steps 1–7 of the audit remediation were implemented; steps 6 (ensemble half),
7 (verification) and 8 (polarity arms) are **code-complete but unrun**, and the final
connectome-vs-null comparison **did not complete**. See *NOT DONE — handed off* at the end.
Nothing in this report is a scientific claim about the connectome. The honest summary is:
the instrument now demonstrably has resolving power, and the corrected comparison has not
yet been run through it.

Machine: Ubuntu-1 (AWS Lightsail, 2 vCPU / 15 GiB, no GPU). Python 3.12.3, `.venv`,
`requirements.txt` pinned. All measurements below are on the E1 pilot subgraph:
top-500 out-degree neurons of MaleCNS v1.0, 23,708 edges, 5 classes, chance = 0.2000.

---

## 1. Bug table

| # | Bug | Fix | Measured before | Measured after |
|---|---|---|---|---|
| 1 | No git repository at all; `e1_pilot.json` overwritten in place, v1–v6 history unrecoverable | `git init`; `.gitignore` excluding `data/raw/`, the 248 MB derived graph, `__pycache__`, `*.pyc`, `.venv`; broken state committed verbatim as `ad1d670` | untracked tree, 1 result file | 9 commits, `ad1d670` preserves the pre-fix state |
| 2 | Results overwritten on every run | `write_result()` → `<prefix>_<UTC>_<git rev>.json`, refuses to overwrite; every result carries a `provenance` block (UTC, git rev, SHA-256 of harness + config) | 1 file, no provenance | 11 versioned result files, none overwritten |
| 3 | `cfg["task_hardening"]` overwritten at L255 before archiving, so archived results misreported their own config | assignment removed | config on disk said `temporal_holdout_noise055_5class_v6`; archived result said `shared_inputs_temporal_phase_only_v2` | archived config is the config that ran |
| 4 | **Probe leakage.** `simulate_driven` had `input_ids` and a docstring promising probes exclude driven inputs; the harness never passed it. 5 of 48 probes were driven input neurons whose spike timing *is* the label | `input_ids=inputs` passed at both call sites; `probe_set()` factored out and draws from the non-input pool only | conn 0.7600 / abs 0.7467 / ER 0.7600 / shuffle 0.7733 / MLP 0.8667 | **0.2000 / 0.3267 / 0.2000 / 0.2000 / 0.2000** (exact chance) |
| 5 | **Dead reservoir.** `syn_scale=0.002` left the network silent | diagnosed via spectral normalisation (§3) | 0 non-input spikes over 450 neurons × 64 steps × 100 trials | first non-input spike at gain 0.5 (`syn_scale` 0.00141); decodable from gain ≈ 5 |
| 6 | `_assert_alive` checked only feature variance, so it was defeated by the leak it existed to catch | `check_alive()` requires non-input spikes > 0 **and** feature variance **and** distinct feature rows; `--allow-dead` records instead of raising, for diagnostic baselines only | guard passed on a silent network | guard raises; `task_validity.valid_for_claims` is now gated on `reservoirs_alive` |
| 7 | Uncontrolled gain: one hand-tuned `syn_scale` for all arms, ρ never computed, arms differed 49.3× | `flylab/spectral.py`; `syn_scale = gain·τ_m/(dt·r·ρ(W))` | ρ never computed; effective gain 0.711 (conn) vs 0.014 (ER) | gain is an explicit swept parameter (§3) |
| 8 | `degree_shuffle` preserved neither structural degree sequence, lost edges, created self-loops | `flylab/nulls.degree_preserving_null`, a directed double-edge swap rejecting self-loops and duplicates, asserting both degree sequences | 23,708 → 21,827 edges (**7.93% lost**), 19 self-loops, structural in/out degree L1 error 1,881 each | 23,708 → 23,708 (**0 lost**), 0 self-loops, 0 duplicates, both degree sequences exact, 99.73% of edges rewired (5 swaps/edge, 1.9 s) |
| 9 | No positive control anywhere in the design | `experiments/harness/positive_control.py`, a gate (§4) | — | gate **PASSES** at 12 seeds; **FAILS** at the harness's own defaults |
| 10 | `flylab/polarity.py` dead default paths | `DEFAULT_ARTIFACT` → `body_polarity_traced.feather`; `data/derived/neurons/polarity_policy.json` written so `DEFAULT_POLICY` resolves | both paths non-existent | both resolve; asserted by `tests/test_polarity.py` |
| 11 | Stale cross-interpreter bytecode (`*.cpython-313.pyc` against a 3.12.3 venv); no dependency pinning | deleted; `requirements.txt` pins installed versions | 4 stale `.pyc` | none; deps pinned |
| 12 | No tests | `tests/` (45 tests) | 0 | 45 passing |

### Where the pre-fix 0.76 came from

A **no-network** linear readout on the raw input drive, using the same 48 probes and the
same 4-bin features, scores **0.9000** on seed 0. Every pre-fix arm scored below that.
The reported numbers were the readout decoding the stimulus; the network was a pass-through.

The audit said this baseline was 0.8667 — that figure is the MLP's score. The direct
no-network linear readout measures 0.9000 on seed 0. Same conclusion, different number.

---

## 2. Corrections to the audit

The audit was right about every bug. Three of its measurements are off:

1. **"0 of 450 non-input neurons ever spike."** Under the harness's actual RNG ordering,
   5 spikes occur across 100 trials × 64 steps × 450 neurons (rate 1.7 × 10⁻⁶). Running the
   identical drive through a **zero matrix** produces the same residual, so those spikes are
   input noise, not the network. Effectively dead, not literally.
2. **"peak v = 0.6463, only 1.55× short of v_th."** With the configured noise (σ = 0.55 on
   every neuron, not just inputs) peak non-input v is **0.8986**; with noise removed it is
   **0.3873**, i.e. **2.58×** short. Neither reproduces 0.6463.
3. **"`degree_shuffle` preserves neither in- nor out-degree."** True for the *structural*
   degree sequence (distinct neighbours; L1 error 1,881 on each side). The *multiset* of
   in- and out-degrees does survive, because permuting `dst` permutes the destination
   multiset. The actual defect is duplicate collision inside `scipy.sparse`: colliding
   `(row, col)` pairs are summed, which is what destroys 7.93% of edges and creates the
   self-loops. Same verdict — not a degree-preserving null — different mechanism.

One thing the audit did not predict, and it matters:

> **The E1 subgraph is inhibition-dominated.** 5,938 inhibitory vs 3,533 excitatory edges;
> signed weight sum −55,861. Its dominant eigenvalue is a large **negative** real,
> −2131.86. So ρ = 1 is an alternating instability, not the excitatory ignition point that
> reservoir-computing intuition assumes, and the audit's suggested sweep range (ρ ≈ 0.3–1.5)
> does not contain this network's useful operating regime.

---

## 3. Spectral radii and the gain sweep

ρ computed per arm on the 500-node subgraph (`flylab/spectral.arm_spectrum`):

| arm | ρ(signed) | ρ(\|W\|) | dominant eigenvalue | nnz |
|---|---|---|---|---|
| `connectome_signed` | 2131.86 | 2182.86 | **−2131.86** (real) | 23,708 |
| `connectome_abs` | 2318.48 | 2318.48 | +2318.48 | 23,708 |
| `er_null` | 43.20 | 259.93 | 41.36 + 12.48j | 23,708 |
| `degree_shuffle` (old, broken) | 1293.00 | 1293.00 | −1293.00 | 21,827 |

Connectome/ER ratio **49.3×**. At the shipped `syn_scale = 0.002` that is an effective gain
of 0.711 for the connectome and 0.014 for its size-matched null — the two arms were never
at comparable operating points, which on its own invalidates every pre-fix comparison.

Sweep: `gain_sweep.py`, 3 seeds, 20 trials/class, 48 probes, gain = 0.3…1.5 in 13 steps plus
2, 3, 5, 8, 12, 20, 30. Mean non-input spikes / mean accuracy per arm:

| gain | syn_scale (conn) | connectome_signed | connectome_abs | er_null | degree_shuffle¹ |
|---|---|---|---|---|---|
| 0.3 | 0.00084 | 0 / 0.200 | 24 / 0.211 | 13 / 0.211 | 74 / 0.356 |
| 0.4 | 0.00113 | 0 / 0.200 | 100 / 0.300 | 110 / 0.233 | 107 / 0.356 |
| 0.5 | 0.00141 | **1 / 0.200** | 256 / 0.333 | 399 / 0.367 | 193 / 0.356 |
| 0.6 | 0.00169 | 8 / 0.200 | 486 / 0.367 | 996 / 0.411 | 270 / 0.378 |
| 0.7 | 0.00197 | 22 / 0.200 | 791 / 0.378 | 1917 / 0.500 | 361 / 0.378 |
| 0.8 | 0.00225 | 45 / 0.200 | 1182 / 0.389 | 3282 / 0.589 | 461 / 0.422 |
| 0.9 | 0.00253 | 81 / 0.211 | 1699 / 0.411 | 5150 / 0.678 | 575 / 0.422 |
| 1.0 | 0.00281 | 128 / 0.222 | 2419 / 0.422 | 7482 / 0.700 | 705 / 0.456 |
| 1.1 | 0.00310 | 189 / 0.222 | 3327 / 0.467 | 10389 / 0.744 | 842 / 0.478 |
| 1.2 | 0.00338 | 264 / 0.233 | 4282 / 0.467 | 13857 / 0.733 | 974 / 0.478 |
| 1.3 | 0.00366 | 330 / 0.278 | 5485 / 0.456 | 17962 / 0.767 | 1115 / 0.522 |
| 1.4 | 0.00394 | 394 / 0.267 | 7666 / 0.500 | 22572 / 0.789 | 1252 / 0.567 |
| 1.5 | 0.00422 | 463 / 0.256 | 13027 / 0.500 | 27864 / 0.778 | 1405 / 0.589 |
| 2.0 | 0.00563 | 784 / 0.344 | 49694 / 0.567 | 74930 / 0.844 | 2202 / 0.700 |
| 3.0 | 0.00844 | 1476 / 0.344 | 88426 / 0.789 | 348404 / 0.922 | 3455 / 0.811 |
| 5.0 | 0.01407 | **2923 / 0.544** | 365812 / 0.944 | 553352 / 0.933 | 5544 / 0.822 |
| 8.0 | 0.02252 | 4518 / 0.611 | 1046488 / 0.978 | 653503 / 0.933 | 8611 / 0.811 |
| 12.0 | 0.03377 | 7238 / 0.722 | 1455304 / 0.933 | 703046 / 0.922 | 12301 / 0.811 |
| 20.0 | 0.05629 | 12640 / 0.722 | 1693809 / 0.900 | 741490 / 0.922 | 18921 / 0.800 |
| 30.0 | 0.08443 | 19311 / 0.744 | 1803723 / 0.900 | 758297 / 0.867 | 39857 / 0.733 |

¹ this column used the **old, broken** shuffle: the sweep ran at commit `25cf1bc`, before the
degree-preserving null landed in `c1ceec1`. It needs re-running.

**Ignition.** First non-input spike in `connectome_signed` at **gain 0.5, `syn_scale`
0.00141**. Accuracy stays at chance until **gain ≈ 5, `syn_scale` ≈ 0.0141**, and only
reaches 0.744 at gain 30. The audit expected threshold crossing near `syn_scale`
0.003–0.004: that bracket (gain 1.07–1.42) is where the *first sparse* spikes appear, which
is the right instinct, but the network does not compute anything there. Note `syn_scale`
0.002814 is exactly gain 1.0 — the shipped 0.002 sat at gain 0.711, just under.

**Matched ρ does not match activity.** At gain 1.0 the four arms fire 128 / 2419 / 7482 /
705 non-input spikes — a ~58× spread. Spectral matching alone does not isolate structure
from excitability, so the downstream comparison was built on **firing-rate matching**
(`flylab/spectral.gain_for_target_rate`, gain bisected per graph).

---

## 4. Positive control — the gate

`experiments/harness/positive_control.py`. Two conditions the instrument must separate,
paired across seeds, requiring |mean difference| ≥ 0.10 **and** a 95% CI excluding zero.

- **PC-A, activity resolution.** Connectome at gain 0.3 vs gain 12.
- **PC-B, structure resolution.** Ring lattice (a delay line) vs Erdős–Rényi: same *n*,
  same edge count, same weight law, all-excitatory in both, gain bisected per graph to match
  non-input firing rate. **Only topology differs.**

| configuration | PC-A | PC-B | gate |
|---|---|---|---|
| 5 seeds × 20 trials/class, 48 probes (**harness defaults**) | 0.2000 → 0.7267, diff **+0.5267 ± 0.0862** ✅ | ring 0.5600 vs ER 0.5933, diff **−0.0333 ± 0.1905** ❌ | **FAILED** |
| 12 seeds × 60 trials/class, 450 probes | 0.2000 → 0.7750, diff **+0.5750 ± 0.0669** ✅ | ring 0.8037 vs ER 0.6583, diff **+0.1454 ± 0.0528** ✅ | **PASSED** |

**The underpowered failure is the important line.** At the settings E1 actually shipped
with, a real +0.15 structural effect measured as −0.03 ± 0.19. The harness could not see an
effect it was built to look for. Between-seed variance dominates (ring ranged 0.267 → 0.900
across seeds at 30 test trials); resolving a ~0.15 effect needs roughly 12 seeds at 60
trials/class. Any connectome-vs-null result produced at 5 × 20 is uninterpretable regardless
of which way it comes out.

Two caveats recorded in the result JSON:

- An all-excitatory ER graph ignites as an avalanche, so its firing rate is nearly
  discontinuous in gain and could not be matched to within 15%: it ends up firing **3.3×
  more** than the ring (0.0351 vs 0.0105). The ring wins while being the *quieter*
  condition, so the residual activity mismatch **opposes** the measured effect rather than
  explaining it (`rate_confound_opposes_effect: true`).
- `make_trials` emits all of class 0, then all of class 1, … so a head slice of the trial
  list is a single class. The gain bisection originally rate-matched on one stimulus
  template; it now strides across classes.

---

## 5. Degree-preserving null — verification

`flylab/nulls.degree_preserving_null`, directed double-edge swap `(a→b),(c→d) ⇒ (a→d),(c→b)`,
rejecting swaps that would create a self-loop or duplicate an existing edge. Measured on the
E1 subgraph, 5 swaps/edge, 1.89 s per draw:

| property | old `degree_shuffle` | `degree_preserving_null` |
|---|---|---|
| edges out | 21,827 of 23,708 (**−7.93%**) | 23,708 of 23,708 (**0 lost**) |
| self-loops | 19 | **0** |
| duplicate edges | (collisions summed silently) | **0** |
| structural out-degree | not preserved (L1 = 1,881) | **exact** |
| structural in-degree | not preserved (L1 = 1,881) | **exact** |
| weight multiset | altered by collision summing | **preserved** |
| fraction rewired | 100% of `dst` permuted | 99.73% |

The broken version is retained as `degree_shuffle_v0_broken` purely so this before/after is
reproducible, with a test asserting it is *not* degree-preserving.

---

## 6. Tests

45 tests, all passing (`.venv/bin/python -m pytest tests -q`). They cover the four failure
modes that were silent, plus the fixes that have no end-to-end run behind them yet:

- `test_no_leakage.py` — probes exclude driven inputs; a decoupled network yields all-zero
  features; the unsafe call is documented by a test so the regression is visible.
- `test_liveness_guard.py` — leaked features pass a variance check while the reservoir is
  provably silent (the exact way the old guard was fooled); the new guard raises.
- `test_nulls.py` — both degree sequences exact, no edge loss, no self-loops, no duplicates,
  weight multiset preserved, deterministic; plus a regression witness that the old shuffle is
  not degree-preserving.
- `test_determinism.py` — same seed → identical features (asserted non-vacuous by requiring
  spikes), different seed → different features.
- `test_spectral.py`, `test_controls.py`, `test_baselines.py`, `test_polarity.py`.

---

## 7. NOT DONE — handed off

Nothing below has produced a measurement. The code exists and compiles; **none of it has
been executed end-to-end**, except where stated.

### 7.1 The corrected connectome-vs-null comparison — NOT RUN

There is **no corrected connectome-vs-null result**. Do not quote one from this repo.

`experiments/harness/null_ensemble.py` is written and smoke-tested (1 seed, 2 draws,
20 trials/class → `e1_ens_smoke_20260915T123557Z_7fee651.json`; that file is a smoke test,
not a result). The full run (`--seeds 0..9 --draws 20 --n-trials 40`) reached seed 8 of 10
at 450.7 s and **died before writing output**. No `e1_null_ensemble_*.json` exists.

What the partial run did establish, and what makes it worth finishing: at matched non-input
firing rate (target 0.002), the **connectome needs gain 11.92** while its degree-preserving
null needs ≈ 1.3 and ER ≈ 0.83. The connectome is roughly 9× harder to excite than its own
degree-preserving null — consistent with the inhibition dominance in §2.

To finish: re-run it. Budget ≈ 40 s/seed plus ≈ 105 s fixed overhead (20 degree-preserving
draws at ≈ 2 s each, plus per-graph ρ and rate matching). 10 seeds ≈ 8.5 minutes. Consider
`--seeds 0,1,2,3,4,5` first to confirm it lands, then extend. **Power warning:** §4 says
~12 seeds are needed to resolve a 0.15 effect; the ensemble averages 20 draws on the null
side, which tightens that side only. The paired difference is still limited by connectome
per-seed variance.

### 7.2 Gain sweep needs re-running for the `degree_shuffle` column — `gain_sweep.py`

The sweep in §3 predates the null fix, so its `degree_shuffle` column is the broken null.
`gain_sweep.py` calls `H.degree_shuffle`, which now delegates correctly, so simply re-running
it fixes the column. ≈ 3 minutes for 3 seeds.

### 7.3 Glutamate polarity sensitivity arm — CODE WRITTEN, NEVER EXECUTED

`experiments/harness/polarity_arms.py` exists and imports cleanly but **has never been run
once**. Treat it as unverified.

Established by direct measurement (not by that script):

- 14,237 of 23,708 subgraph edges (**60.05%**) have presynaptic sign UNKNOWN, so they carry
  weight exactly zero. `connectome_signed` is a ~40%-edge subsample of the connectome.
- Those zeros are stored as explicit zeros and counted by `ops_proxy`, inflating the energy
  proxy by 23,708 / 9,471 = **2.503×**. `ops_proxy` in `e1_reservoir.py` still uses
  `W.nnz`; it should use the count of structural non-zeros.
- Subgraph sign balance: 3,533 excitatory, 5,938 inhibitory, 14,237 zeroed.
- MaleCNS v1.0 `consensus_nt` across all 1,835,518 rows: unclear 1,671,117, acetylcholine
  104,193, **glutamate 29,443**, gaba 22,196, histamine 8,024, dopamine 396, octopamine 101,
  serotonin 48.

`flylab/polarity.py` now exposes three named policies — `glutamate_unknown` (as shipped,
default, kept as the reference arm), `glutamate_inhibitory` (GluClα), `glutamate_excitatory`
(opposite sensitivity bound) — plus `sign_of` / `sign_series`, mirrored in
`data/derived/neurons/polarity_policy.json`. Monoamines stay UNKNOWN by design.

**Still missing:** run `polarity_arms.py` across all three policies and report the effect of
the choice on sign composition, ρ, ignition gain, `ops_proxy` and accuracy; then write the
documented decision. Expect ≈ 1–2 minutes at 8 seeds × 40 trials/class. Note that making
glutamate inhibitory will push an already inhibition-dominated graph further that way, which
may move the ignition point substantially.

### 7.4 Parameter-matched MLP — CODE WRITTEN, NEVER RUN IN THE FULL HARNESS

`mlp_width_for_budget` in `e1_reservoir.py` is unit-tested and correct: for the 192-feature
readout (965 params) it picks width 5 → **995 params, +3.1%**, inside PROTOCOL.md:24's ±10%.
The shipped width-32 MLP had **6,341 params, 6.57× over budget**, so the 0.8667 it scored was
never a matched baseline. `run_seed` and `null_ensemble.py` both call it with
`param_budget=`, but **no full harness run has been executed since that change**. There is no
post-fix MLP number.

### 7.5 Ridge sweep — CODE WRITTEN, NEVER RUN IN THE FULL HARNESS

`ridge_sweep` replaces the hardcoded `ridge=10.0` with a 12-point grid (1e-4 … 1e4),
selecting on a validation split of **train only** and recording train accuracy, test accuracy
and the train/test gap at every point. Wired into `run_seed` and `null_ensemble.py`, unit
tested, **never run end-to-end**. The train/test-gap-versus-regularisation curve the audit
asks for has not been produced.

### 7.6 Smaller items

- `ops_proxy` still counts explicit zeros (see §7.3).
- `experiments/harness/e1_reservoir.py` `main()` has not been run since the spectral-gain,
  ridge-sweep and MLP-budget changes landed. The only full-harness run on record is the
  leak-fixed dead-net baseline at commit `686e757`, predating all three.
- `e1_config.json` still has `gain_normalization` unset, so `lif_for_arm` defaults to
  `mode="none"` and uses the raw `syn_scale=0.002`. To run the harness at a controlled gain,
  add `"gain_normalization": "spectral_signed"` and `"gain": <value>` under `dynamics`.
  Nothing currently sets these; only the standalone scripts normalise gain.
- Commit `7fee651` is an accidental empty commit titled `noop`. History was deliberately not
  rewritten.
- The step-7 baseline changes were committed together with step 6 in `c1ceec1` /`13bb88e`
  rather than as their own commit.

---

## 8. Result files

All under `experiments/results/`, none overwritten. Pre-fix files preserved; see
`experiments/results/README.md`.

| file | what it is |
|---|---|
| `e1_pilot.json` | **pre-fix, invalid** — the leaked 0.76/0.76/0.77/0.87 |
| `e1_pilot_20260915T121046Z_686e757.json` | leak-fixed dead-net baseline (misnamed prefix; a `--prefix` bug was fixed straight after) |
| `e1_leakfixed_deadnet_20260915T121124Z_686e757.json` | leak-fixed dead-net baseline, correctly named — all arms at chance |
| `e1_gain_sweep_20260915T121555Z_25cf1bc.json` | the §3 sweep (old `degree_shuffle` column) |
| `e1_positive_control_20260915T122213Z_3bd93f0.json` | gate **FAILED**, 5 seeds × 20 trials |
| `e1_positive_control_20260915T122911Z_3bd93f0.json` | gate **PASSED**, 12 seeds × 60 trials |
| `e1_gain_smoke_*`, `e1_pc_smoke*`, `e1_ens_smoke_*` | smoke tests, not results |
