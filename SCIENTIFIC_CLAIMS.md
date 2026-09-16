# Scientific claims — Fly Lab

**Rule:** a claim is only as complete as its protocol. Code existing, a JSON existing, or a flag in `PROJECT_STATE.json` does not make a scientific result. This file lists only statements that can be tied to artifacts on this machine. Last inspection: git tip `3dbe1d9` (`cursor/exp-inst-001-c6ad`), Ubuntu-1, 2026-09-16.

The connectome is the scientific object. Applications are testbeds. Negative results are valuable if valid. Do not assume Fly wins.

---

## How to read status

| Status | Meaning |
|---|---|
| **ENGINEERING TRUE** | Pipeline/code/tests did what they say. Not a biology or topology result. |
| **MEASURED** | A number exists in a result file. Attach the protocol. |
| **CLOSED (hypothesis ID)** | Do not rerun this ID to rescue a win. The ID is retired. |
| **NOT SCIENTIFICALLY COMPLETE** | The ID or measurement cannot be cited as a finished scientific result. |
| **OPEN** | Not decided by valid evidence. |
| **INVALID / DO NOT CITE** | Known confound or leakage. Keep the file; do not use the number. |

---

## 1. Dataset / graph (E0)

**Claim:** MaleCNS v1.0 feathers on disk, SHA-256 locked, Traced↔Traced filter yields 165,122 neurons, 25,563,197 directed edges, Σw = 124,025,046.

- **Status:** MEASURED on disk. Engineering pipeline exists (`scripts/build_graph.py`).
- **Evidence:** `data/manifests/source.lock.json`, `data/manifests/e0_diagnosis.json`, `data/derived/graph/graph_meta.json`, `system/build_graph.log`.
- **Not claimed:** identity with published ~166,700 / ~25,582,938 (documented deltas; not forced).
- **Hole:** `graph_meta.json` is gitignored. It predates the restored `build_graph.py` (mtime 10:28 vs script 12:52). Current script would write extra keys (`polarity_policy`, `validation_targets`, `delta`, `artifacts`) that the on-disk meta lacks. Rebuild against the default out-dir would overwrite every result’s graph. Reproducibility of the derived graph from the script in git is **OPEN**.

---

## 2. Instrument repairs (not topology results)

| Statement | Status | Evidence |
|---|---|---|
| Probe/readout leakage closed: `input_ids` reach `simulate_driven`; probes exclude driven units | MEASURED in tests + leak-fixed run | `tests/test_no_leakage.py`; `experiments/harness/e1_reservoir.py` `probe_set` / `reservoir_features` |
| At shipped `syn_scale=0.002` with leak closed, connectome/ER/shuffle/MLP score chance 0.2000 | MEASURED | `experiments/results/e1_leakfixed_deadnet_20260915T121124Z_686e757.json` (`connectome_abs` 0.327) |
| `check_alive()` requires non-input spikes, not feature variance | ENGINEERING TRUE in `e1_reservoir.run_seed` and unit tests | `tests/test_liveness_guard.py` |
| `check_alive()` is called by `null_ensemble.py`, `polarity_arms.py`, or `anomaly/` | **FALSE** — only `e1_reservoir.py` + tests reference it | repo grep 2026-09-15 |
| Degree-preserving null preserves in/out degree, loses 0 edges, 0 self-loops | MEASURED on E1 subgraph draws | `flylab/nulls.py`; `tests/test_nulls.py`; `null_diagnostics` in powered JSON |
| E1 top-500 subgraph is inhibition-dominated; signed λ ≈ −2131.86 | MEASURED | powered JSON `spectra.connectome_signed`; polarity JSON E=3533 I=5938 zero=14237 |
| `glutamate_unknown` zeroes 14,237 / 23,708 subgraph edges (60.05%) | MEASURED | polarity JSON `fraction_zeroed` |
| PC-A and PC-B pass | MEASURED **only** at 450 probes, target_rate 0.01, all-excitatory, 12×60 | `e1_positive_control_20260915T122911Z_3bd93f0.json` `gate_passed: true` |
| PC-B at 48 probes | MEASURED FAIL at target_rate **0.01**, 5×20 (not 0.002) | `e1_positive_control_20260915T122213Z_3bd93f0.json` `gate_passed: false` |
| `INSTRUMENT_VALID_E1` (EXP-INST-001) | MEASURED **TRUE** at 48 / 0.002 / signed / 12×60 under a **constructed** feature-injection gate (not stock ring-vs-ER PC-B) | `experiments/results/EXP-INST-001/summary.json`; `conclusion.json` |

`e1_config.json` still ships `syn_scale: 0.002` and no `gain_normalization`. Default harness path remains the dead-net baseline unless a standalone runner sets gain.

**EXP-INST-001 residuals (not topology):** positive-arm acc = 1.0 on all 12 seeds; realized Δacc = 0.365 ± 0.116 vs synthetic lock 0.15. Null pair Δ = 0.00185, CI includes 0; empirical FP over 19 perm-gates = 0. Seed 9 still 306 non-input spikes / no-injection acc 0.200 (same as powered E1) and was kept because `check_alive.alive` is `pool_spikes>0`. Stock all-excitatory PC-B at 48/0.002 was not run. This is an instrument result. It does not reopen `E1_TOPOLOGY_ADVANTAGE` or EXP-006.

`e1_config.json` still ships `syn_scale: 0.002` and no `gain_normalization`. Default harness path remains the dead-net baseline unless a standalone runner sets gain.

---

## 3. E1 topology advantage

**Hypothesis ID:** `E1_TOPOLOGY_ADVANTAGE`  
**ID status:** CLOSED (`docs/E1_TOPOLOGY_ADVANTAGE.md` value `FALSE`).  
**Scientific completeness:** NOT SCIENTIFICALLY COMPLETE.

**Only valid statement:** The tested implementation/configuration did not demonstrate a topology advantage under that experimental setup.

**Do not say:** biological topology has no value; the result is a publishable finished negative; “rate-matched” without the seed-0 caveat.

**Measured numbers** (artifact `experiments/results/e1_null_ensemble_powered_20260915T130422Z_fe089d3.json`, **untracked**):

| Arm | Mean acc | CI as stored | CI kind |
|---|---|---|---|
| connectome_signed | 0.634 | ±0.122 | 12 seeds |
| ER null | 0.651 | ±0.017 | 20 draws (`ci95_over_draws`) |
| degree-preserving null | 0.685 | ±0.030 | 20 draws |
| MLP on connectome features | 0.642 | ±0.123 | 12 seeds |

Paired diffs vs DP −0.051 ± 0.110 and vs ER −0.017 ± 0.131; both CIs include 0.

**Protocol defects that keep this incomplete:**

1. No **stock** PC-B (ring vs ER) at 48 probes / rate 0.002 / signed. EXP-INST-001 recorded `INSTRUMENT_VALID_E1=TRUE` on a constructed feature-injection gate at that config; that does not rewrite this closed ID.
2. Gain matched once on seed 0; connectome seed 9 had 306 non-input spikes (target ~17,280) and acc 0.200, still averaged. Reproduced on EXP-INST-001 no-injection arm.
3. Runners did not call `check_alive()`.
4. No no-network / label-permutation row in the table.
5. ER null is not topology-only (sign balance, weight law, effective nnz).
6. Two CI kinds mixed in prose tables (`docs/PORTFOLIO_BRIEF_FOR_CLAUDE.md`).

Do not rerun this ID to rescue a win. A future protocol-valid comparison, if any, must be a **new ID** (see `EXP-E1B-001` in `RESEARCH_ROADMAP.md`).

**Pre-fix 0.76 ≈ ER/shuffle:** INVALID / DO NOT CITE. Label leak + dead reservoir (`e1_pilot.json`, `reports/E1_audit_fixes.md`).

---

## 4. Glutamate polarity

**Claim sometimes written:** accuracy is insensitive to glutamate mapping.  
**Status:** OPEN / underpowered.  
**Measured:** 8 seeds × 40 trials/class (below PROTOCOL 12×60). Unknown vs inhibitory Δacc 0.000 ± 0.062; vs excitatory −0.050 ± 0.161. Zeroing and ops inflation **are** measured.  
**Artifact untracked:** `e1_polarity_arms_20260915T140857Z_fe089d3.json`.

---

## 5. Anomaly topology advantage (EXP-006)

**Hypothesis ID:** `ANOMALY_TOPOLOGY_ADVANTAGE` / EXP-006  
**ID status:** CLOSED. No EXP-007/008/009 topology hunt.  
**Scientific completeness:** NOT SCIENTIFICALLY COMPLETE.

**Only valid statement:** The tested implementation/configuration did not demonstrate a topology advantage under that experimental setup.

**Measured AUROC (12 seeds, subtle glitch):** fly_signed 0.519 ± 0.027; ER 0.534 ± 0.030; weight_perm 0.527 ± 0.033; threshold 0.733 ± 0.017; hubs_removed **identical** to fly_signed on all 12 seeds.

**FLAG (do not rewrite historical files):** `experiments/results/EXP-006/EXP006_SUMMARY.json` sets `"no_post_hoc_tuning": true` while `anomaly/metrics.summarize` → `fpr_fnr_at_f1` selects the F1 threshold on **test** labels. AUROC/AUPRC are threshold-free; F1/FPR/FNR in V1 tables are oracle operating points.

Other defects: no gate in `anomaly/`; `gain=5.0` not rate-matched; `fly_scorer.make_W_post_pre(er_null)` uses `rng(0)` (EXP-001–005); per-window z-score in `encode_to_current`; EXP-005 “temporal hold-out” on i.i.d. copies of one template.

Anomaly V1 EXP-001–005: single seed each; JSONs set `claim_ready: false`. Tables in `anomaly/ANOMALY_RESULTS.md` are not claim-ready.

---

## 6. Anomaly Detector V2

**`ANOMALY_V2_REAL_SENSOR`:** ENGINEERING TRUE. Not a research-program result. Not a connectome result.

**Measured** (`reports/ANOMALY_V2.md`, `anomaly/results/v2_nab_machine_temperature_*.json`): one NAB series (`machine_temperature_system_failure`); chronological split; val max-F1 threshold (V2 path); test frozen. Threshold test AUROC 0.943, AUPRC 0.746; rolling z 0.466 / 0.184; OCSVM 0.658 / 0.559; optional fly 0.431 / 0.083.

**Not claimed:** NAB leaderboard, camera/IMU/mic hardware, topology, animal intelligence.

Do not spend more research budget on this milestone.

---

## 7. What is not a claim

- `PROJECT_STATE.json` on tip `0f08d20` records V2 engineering flags and **omits** `E1_TOPOLOGY_ADVANTAGE` (that key exists on `main` at `11956c4`). A JSON flag is not a result.
- `experiments/registry.json` still says the powered ensemble is `running` (pid 11104). Stale.
- `docs/PORTFOLIO_BRIEF_FOR_CLAUDE.md` “publishable negative” / “45 unit tests” (58 pass now) — do not copy.
- LSTM/GRU: deferred; no GPU. Not faked.
- Camera / IMU / microphone adapters: stubs.
- Full-connectome (165k) powered dynamics: not run.

See `RESEARCH_ROADMAP.md` for what to do next and `reports/RESEARCH_AUDIT_ROADMAP.md` for the A–L audit.

- The pre-INST exploratory pilot at `experiments/results/EXP-MEM-001/pilot_superseded/pilot_20260916T011917Z_dcc995f.json` is **SUPERSEDED/INVALIDATED**; it is not confirmed and is not cited as a memory result.
- The post-INST MEM sizing tranche at `experiments/results/EXP-MEM-001/post_inst_20260916T030347Z_dcc995f/sizing/summary.json` is **INVALIDATED** by failed required liveness/rate-match checks; it produced no memory curve or power estimate and is not evidence for or against memory. The one preregistered accuracy-blind mapping repair also failed required liveness in five cells (`experiments/results/EXP-MEM-001/post_inst_mapping_repair_20260916T031717Z_dcc995f/sizing/summary.json`). **Allowed recap:** “Bajo el mapa random y el repair top-50, controles estructurales quedaron silenciosos en 5 celdas; AUC primario n=0; no hay evidencia válida de memoria ni de ventaja topológica en ese protocolo.” No EXP-A or GLU result was run on EXP-MEM-001. `EXP-MEM-002` is now preregistered and in progress as an accuracy-blind instrument check; it is not a scientific memory result.
- `EXP-MEM-002` Q0 is **INSTRUMENT_INCOMPLETE**: all 72 registered cells were written, but no delay had all five arms live and rate-matched across both splits and 12 seeds; 263 arm/cell rows are `MISSING`. This is not a topology result and no accuracy/AUC/curve was computed. Map 2 is the one registered follow-up (`experiments/results/EXP-MEM-002/protocol_map2.md`).
- `EXP-MEM-002` map 2 is also **INSTRUMENT_INCOMPLETE**: all 72 cells were written, no delay was complete, and 277 arm/cell rows are `MISSING` (connectome 62, DP 38, weight permutation 52, ER 56, ring 69). No accuracy/AUC/curve was computed. The one permitted map change is exhausted; E1 fail-closed hygiene is recorded in commit `dfdf7dd`, with 72 tests passed at that historical checkpoint; the current full suite is 74 passed after the bounded A2A regression tests.


## 8. EXP-MEM-003 — primary pair instrument

Status: MEM_003_NO_PAIR; claim-ready: false.

Measured: the preregistered top_positive_indegree map wrote 72/72 cells and
had no eligible delay. The one preregistered hash_ranked fallback also wrote
72/72 cells and had no eligible delay. In the fallback, individual live rows
were connectome 4/72, DP 12/72, weight permutation 10/72, ER 0/72, and ring
0/72; no delay contained a live, rate-matched connectome-plus-DP pair.

Interpretation: no memory curve, paired contrast, or EXP-A-001 result was
produced. This is an instrument outcome under this protocol, not evidence that
the connectome has no memory and not evidence that topology has no value.
MEM-001 and MEM-002 remain closed in their recorded states. The next branch is
EXP-GLU-001, polarity sensitivity only.


## 9. EXP-GLU-001 — glutamate polarity sensitivity

Status: COMPLETE_METRIC_WITHHELD; claim-ready: false.

Measured: all 12 seed checkpoints were written. Valid seed counts were
glutamate_unknown 8/12, glutamate_inhibitory 6/12, and
glutamate_excitatory 8/12. The preregistered all-policy paired comparison was
withheld because required 12-seed validity was not met. Missing rows were due
to train/test rate-band failures and one liveness failure in the unknown and
inhibitory policies.

Interpretation: this is a sensitivity/instrument outcome only. No aggregate
polarity delta is a claim, and this result says nothing about memory,
topology advantage, or profitability.


## 10. EXP-IGNITE-001 — primary pair ignition

Status: NO_COIGNITE; claim-ready: false.

Measured: smoke found 0 pair cells, sizing found 0 pair cells, and the 12-seed
confirm found 0 pair cells. All confirm checkpoints were written under the
frozen hash-ranked map, 16-point gain grid, 0.002 target rate, and 20% train/test
band.

Interpretation: no accuracy was computed. This is an operating-point instrument
outcome, not evidence that the connectome has no memory, that topology has no
value, or that Fly lost. MEM-004 is not authorized from this result.


## 11. EXP-IGNITE-002 — polarity co-ignition sensitivity

Status: NO_COIGNITE; claim-ready: false.

Measured: smoke found 0 pair cells, sizing found 0 pair cells, and the 12-seed
confirm found 0 pair cells. The primary comparison used the same hash-ranked
map, 16-point gain grid, 0.002 target rate, and 20% train/test band while
varying only glutamate policy: `glutamate_unknown` versus
`glutamate_inhibitory`. All 12 confirmation checkpoints were written.

Interpretation: no accuracy was computed. This is an operating-point/polarity
instrument outcome, not evidence that the connectome has no memory, that
topology has no value, or that one biological polarity is correct. No further
IGNITE ID is authorized by this queue.


## 12. TRACK-7-QUEUE — bounded CPU research queue

Status: QUEUED_2VCPU; claim-ready: false.

Measured: no experiment was executed. The marker records prerequisites for a
future small continual-learning or architecture smoke: frozen task/split,
positive control, independent liveness/rate gates, no-network baseline, and
explicit compute budget.

Interpretation: this is documentation, not evidence about memory, topology,
architecture, biology, or profitability. The current handoff authorizes no
new scientific ID after EXP-IGNITE-002.
