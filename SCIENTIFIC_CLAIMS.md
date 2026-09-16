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

## 13. ROUTING-002 — calibration envelope

Status: CALIBRATION_ONLY_COMPLETE; claim-ready: false.

Measured from the fixed nine-point gain grid and 12 seeds: the reference target
0.002 within relative tolerance 0.15 was reachable in connectome_signed 0/12,
degree_preserving 1/12, and block_preserving 5/12 seeds. Mean maximum grid
rates were 0.015227141203703706, 0.26948464765847574, and 0.1831652866809117,
respectively.

Interpretation: the incomplete ROUTING-001 primary contrast is explained by a
tested operating-point envelope mismatch. ROUTING-002 computed no task,
routing, memory, topology-advantage, biological, or ML metric. The envelope
difference itself is not a routing advantage.

The immutable summary is
research/results/ROUTING-002/FULL_20260916T200427Z_2ddf9b49748e/summary.json
with SHA256
8b37c5b50780c3e8a35f3adcda4fce265aceb57fef8166ec8605454601cc8325.

## 14. ROUTING-003 — operating-point replication

Status: INCONCLUSIVE; claim-ready: false.

At the preregistered calibration-derived target rate 0.013 ±15%, the positive
control passed 12/12. Connectome_signed and degree_preserving were measured in
12/12 seeds. Block_preserving was measured in 8/12; seeds 2, 4, 6, and 8 were
MISSING because calibration did not reach the target within the frozen gain
range/tolerance.

The available paired connectome-minus-block contrast was n=8, mean
-0.07031250000000004, CI95 [-0.14872401153071557, 0.008099011530715503].
This is inconclusive. It is not evidence for or against topology, biology, or
ML transfer. The missing rows are an instrument/operating-point outcome, not
negative task results.

## 15. MOTIF-MINE-001 — directed motif inventory

Status: STRUCTURAL_MEASURED; claim-ready: false.

On the fixed 500-node induced subgraph (9,469 simple directed edges), the
observed directed 3-cycle count was 85. Twenty degree-preserving nulls had mean
84.85 and sample SD 0.36634754853252327. The observed feed-forward occurrence
count was 62,611; the null mean was 25,254.5 with sample SD 237.1900193160705.

Interpretation: feed-forward occurrences were enriched relative to this
degree-preserving null, while directed 3-cycles were not materially separated.
The feed-forward statistic is non-induced: reciprocal extra edges are allowed
and contribute additional ordered occurrences. This is structural evidence
under one subgraph and null family, not evidence of biological function,
novelty, or an ML primitive. A block-preserving control is required.

## 16. MOTIF-MINE-002 — block-preserving control

Status: STRUCTURAL_MEASURED; claim-ready: false.

Using the same 500-node, 9,469-edge subgraph, the observed non-induced
feed-forward occurrence count was 62,611. Twenty nulls preserving directed
in/out degree and superclass source-to-destination block counts had mean
36,682.15 and sample SD 280.39319666647066, giving an observed-minus-null delta
of 25,928.85. Directed 3-cycles were 85 observed versus null mean 84.95 and SD
0.22360679774997896.

Interpretation: the feed-forward enrichment survives the tested degree-plus-
block null, while cycles do not separate. The statistic is non-induced and the
null does not preserve reciprocity or spatial/neuropil structure. This remains
a structural candidate, not evidence of biological function, novelty, or an ML
operator. The induced-motif control is required next.

## Motif cycle-count audit correction

The directed-cycle submetrics in MOTIF-MINE-001 and MOTIF-MINE-002 are
invalidated. Their helper multiplied boolean sparse matrices, whose diagonal
indicates vertices participating in at least one closed walk rather than the
number of cycle occurrences. The historical cycle values and null comparisons
must not be cited. The feed-forward calculations used dense integer adjacency
and are unaffected. MOTIF-MINE-003 uses explicit induced-cycle enumeration.

## 17. MOTIF-MINE-003 — induced motif control

Status: STRUCTURAL_MEASURED; claim-ready: false.

With reciprocal extra edges excluded, the observed induced feed-forward count was
15,740. Twenty degree-preserving nulls had mean 18,953.1 and SD 266.9985018684562;
twenty degree-plus-superclass-block nulls had mean 22,673.05 and SD
383.730644977355. The observed induced 3-cycle count was 354, versus degree
null mean 1,734.15 (SD 78.59441188117236) and block null mean 1,566.1 (SD
69.25080276943024).

Interpretation: the earlier non-induced FFL enrichment does not survive the
induced definition; it depended on reciprocal/extra-edge structure. The
induced counts are lower than the tested nulls. This falsifies the tested
feed-forward enrichment candidate under this control, but is not a claim that
biology lacks the motif or that topology is generally inferior.

## Motif edge-presence audit correction

MOTIF-MINE-001, MOTIF-MINE-002, and MOTIF-MINE-003 are invalidated as full
topology motif analyses. Their runners converted signed weights to boolean
adjacency and therefore dropped UNKNOWN zero-weight edges, contrary to the
protocols' directed-edge presence definition. Historical artifacts are
preserved but their motif counts, deltas, and cycle/FFL interpretations are not
claimable. A corrected unsigned-edge analysis is registered as MOTIF-MINE-004.



## 18. MOTIF-MINE-004 — corrected unsigned-edge topology

Status: STRUCTURAL_MEASURED; claim-ready: false.

The corrected run used the full unsigned edge presence of the fixed 500-node
subgraph, retaining UNKNOWN zero-weight edges, removing 4 source self-loops,
and analyzing 23,704 directed edges. All 20 degree-preserving and all 20
superclass-block-preserving nulls completed; 40/40 null invariant checks passed.

Observed non-induced FFLs were 490,588, versus degree-null mean 250,756.2
(SD 988.9078292423628) and block-null mean 351,624.5 (SD 893.6798849935615).
Observed induced FFLs were 72,245, versus degree-null mean 142,679.65
(SD 1,756.1283454774805) and block-null mean 133,260.15
(SD 1,487.4813851113). Observed induced 3-cycles were 4,276, versus
degree-null mean 32,600.2 (SD 618.9381909452077) and block-null mean 22,528.65
(SD 438.8594397922151).

Interpretation: the unsigned topology contains a measured mixed motif signature:
non-induced FFL occurrences are enriched, but exact induced FFLs and induced
cycles are depleted under both tested null families. This does not identify a
computational primitive, biological mechanism, novelty, or ML advantage.
MOTIF-MINE-001/002/003 remain invalidated historical implementations and their
numbers are not used for this claim.

Artifact: research/results/MOTIF-MINE-004/FULL_20260916T205754Z_2ddf9b49748e/summary.json
SHA256: a8c402c0df1e02116931a6c278f35fba94aa7a96bd29c31c273c54029bd1d109

Adversarial decision: do not call this a breakthrough. Run the preregistered
signed-polarity composition screen next; it can test whether the mixed
signature is explained by edge polarity rather than motif abundance.


## Correction: MOTIF-MINE-004 induced counter

An adversarial code audit found that MOTIF-MINE-004's induced FFL branch
excluded reverse edges top-to-middle and sink-to-top but omitted sink-to-middle.
Therefore its induced FFL count and any claim relying on M4 induced abundance
are invalidated. The M4 non-induced FFL count remains a separate non-induced
measurement. M4's immutable artifacts are preserved and not overwritten.

SPECIALIZATION-001 independently checks all three reverse edges in its own
induced enumeration; its observed induced total is 33,551 and remains
provisional pending cross-check against MOTIF-MINE-005. A new preregistered
MOTIF-MINE-005 repeats the unsigned topology measurement with the corrected
condition.


## 19. MOTIF-MINE-005 — corrected induced topology

Status: STRUCTURAL_MEASURED; claim-ready: false.

MOTIF-MINE-005 is the corrected replication of the M4 induced-motif branch.
It uses 23,704 unsigned directed edges on the fixed 500-node subgraph after
removing 4 source self-loops, with all UNKNOWN zero-weight edges retained.
All 20 degree-preserving and 20 superclass-block-preserving nulls completed;
40/40 invariant checks passed.

Observed non-induced FFLs were 490,588, versus degree-null mean 250,756.2
(SD 988.9078292423628) and block-null mean 351,624.5
(SD 893.6798849935615). Observed induced FFLs were 33,551, versus degree-null
mean 115,093.45 (SD 1,936.1172342440532) and block-null mean 92,977.55
(SD 1,331.4288515884375). Observed induced 3-cycles were 4,276, versus
degree-null mean 32,600.2 (SD 618.9381909452077) and block-null mean 22,528.65
(SD 438.8594397922151).

Interpretation: the corrected unsigned topology shows non-induced FFL
enrichment but depletion of exact induced FFLs and cycles under both nulls.
The non-induced signal is compatible with extra-edge/reciprocal closure; it is
not evidence of a reusable operator, biological function, novelty, or ML
advantage.

Artifact: research/results/MOTIF-MINE-005/FULL_20260916T212407Z_2ddf9b49748e/summary.json
SHA256: f363c6310324f0ea555b399f470af3e1cfd9319a9071602bbf3afd75252909c6

## 20. SPECIALIZATION-001 — signed composition

Status: STRUCTURAL_MEASURED; claim-ready: false.

On the same corrected topology, the observed induced FFL total was 33,551:
1,303 all-positive, 11,359 with any inhibitory edge, and the remainder
containing UNKNOWN edges. The observed all-positive count was 1,303 versus
degree-null mean 441.6 (SD 31.1387387771499) but block-null mean 2,707.1
(SD 152.35654166944616). Any-inhibitory count was 11,359 versus degree-null
mean 65,044.35 (SD 854.5918246988473) and block-null mean 36,261.6
(SD 635.4334948016113). Full ordered pattern counts and all 40 null draws are
stored in the immutable summary.

Interpretation: sign composition is structurally non-random under these
rewires, but the apparent all-positive enrichment is not robust to the tested
block-preserving null. UNKNOWN annotation and topology/sign attachment are
major confounds. No biological neurotransmitter, functional routing, novelty,
or ML claim is licensed.

Artifact: research/results/SPECIALIZATION-001/FULL_20260916T211104Z_2ddf9b49748e/summary.json
SHA256: 7bf11f16683bf648626f5f1482f3bb65bf9325061b1048d811fc345ba44c33b2


## 21. MOTIF-MINE-007B — degree plus reciprocity complement

Status: STRUCTURAL_MEASURED; claim-ready: false.

This complementary null preserved exact directed in/out degrees and reciprocal
pair count but intentionally did not preserve superclass blocks. All 20 nulls
completed their 204,280 singleton and 134,900 reciprocal-unit swaps, and all
20 passed edge, degree, loop, duplicate, and reciprocal-pair invariants.

Observed non-induced FFLs were 490,588 versus null mean 240,957.95
(SD 1,497.421695518843). Observed induced FFLs were 33,551 versus null mean
23,621.65 (SD 143.76379567668775). Observed induced 3-cycles were 4,276
versus null mean 4,212.1 (SD 70.64805282823478).

Interpretation: preserving reciprocity explains a substantial part of the
non-induced contrast seen against degree/block nulls, but a residual contrast
remains under this complementary null. The induced FFL count is also above
this null, while cycles are close to it. Because M7B breaks superclass blocks,
the residual cannot be assigned to motifs rather than block/spatial structure.
No function, biology, novelty, or ML claim is licensed.

Artifact: research/results/MOTIF-MINE-007B/FULL_20260916T220944Z_2ddf9b49748e/summary.json
SHA256: d97d710a8373d12b25305ecbe82305dbe2f48764370925148d0291b4594b86b7


## 22. MOTIF-FUNC-001 — signed functional readout

Status: PASS for the predeclared locked readout; claim-ready only at this
narrow scope.

The positive control passed 12/12. The observed signed graph was measured in
12/12 seeds. The global degree+reciprocity null was measured in 11/12; seed 1
was MISSING because its independent rate calibration was not accepted and was
not scored as a negative. All measured train and test splits passed liveness.

For the 11 paired seeds, observed-minus-null routing margin had mean
0.17613636363636365, SD 0.04204374825912604, and 95% t interval
[0.14789098922690247, 0.20438173804582482]. The predeclared gate of at least
8 paired seeds with an interval excluding zero passed in the observed-positive
direction.

Interpretation: under this locked LIF task and this degree+reciprocity null,
the observed signed graph produced a higher routing margin. This does not
attribute the difference to FFL motifs, biology, novelty, or transferable ML:
M7B intentionally broke superclass blocks, and the comparison can reflect
block/spatial organization, weight placement, or other structure. Paper-style
readout evidence is not live profitability or general intelligence evidence.

Audit artifact:
research/results/MOTIF-FUNC-001/AUDIT_20260916T222412Z_2ddf9b49748e/summary.json
SHA256: e76f6078e11a563dad3d6165fc02225714c2ccf616649c10b65f09badb5092dd


## 23. MOTIF-FUNC-002 — fixed-topology weight-placement control

Status: PASS for the predeclared locked readout; claim-ready only at this narrow
scope.

The run kept the selected edge coordinates and topology fixed and globally
permuted the frozen signed weights independently by seed. The selected
subgraph had 23,708 records before removal of 4 source self-loops and 23,704
records in the run; UNKNOWN zero-weight records remained part of the topology.
The positive control passed 12/12. Both observed and weight-permuted arms were
measured in all 12 seeds, and all measured train/test liveness checks passed.

The paired observed-minus-weight-permuted routing-margin difference was mean
0.12847222222222224, SD 0.06395610210631195, with 95% t interval
[0.08783645362404835, 0.16910799082039613]. The preregistered gate passed in
the observed-positive direction.

Interpretation: for this locked LIF readout, the observed placement of signed
weights produced a higher routing margin than a global weight permutation on
the identical topology. This is a functional readout result, not a motif
attribution: it does not establish biological function, novelty, general
topology advantage, or ML transfer. It also does not separate fine-scale
weight placement from block/spatial structure in the broader M1 comparison.

Artifact: research/results/MOTIF-FUNC-002/FULL_20260916T223250Z_2ddf9b49748e/summary.json
SHA256: 39e80711efaac422e520967cc8dac312179a3f9c2abdca7ec929b3f0d08cae85
Independent audit: research/results/MOTIF-FUNC-002/AUDIT_20260916T223620Z_2ddf9b49748e/summary.json
Audit SHA256: b7fef5e54d19fb8244d2ce847f93bc60a75edfb5aed823832cf714a811307760
Pre-run protocol SHA256: 4a6c2b37f3b876b1c3e3fd693b3cf371d8dd0a3a74d6458e16bee2e1d15f52a0
Current protocol SHA256 after wording correction: c8b01dc98458fbdcbd2d502b16be4df96423b187de45ad9d5aedb5105e720d03


## 24. MOTIF-FUNC-003 — within-block weight-placement control

Status: PASS for the predeclared locked readout; claim-ready only at this narrow
scope.

The run fixed the selected edge coordinates and topology and permuted signed
weights independently within each source-superclass to destination-superclass
block. The positive control passed 12/12. Observed and block-weight-permuted
arms were measured in all 12 seeds, and every measured train/test liveness
check passed. The permutation preserved the all-edge weight multiset and each
block's weight multiset, as well as edge count, node degrees, blocks, and
reciprocal-pair count.

The paired observed-minus-block-weight-permuted routing-margin difference was
mean 0.12847222222222224, SD 0.07262296549883594, with 95% t interval
[0.08232979134020302, 0.17461465310424146]. The preregistered gate passed in
the observed-positive direction.

Interpretation: in this locked LIF task, coarse block weight composition alone
did not account for the observed readout difference; within-block signed-weight
placement remained relevant under this control. This does not identify a
biological function, motif, novelty, general topology advantage, or transferable
ML benefit. It remains vulnerable to task/readout limitations and does not by
itself separate sign placement from magnitude placement.

Artifact: research/results/MOTIF-FUNC-003/FULL_20260916T224042Z_2ddf9b49748e/summary.json
SHA256: fab7b7e5118a5da65ddc1aeac36de7f8a274c2fd3857decda65934b3fba6e01c
Independent audit: research/results/MOTIF-FUNC-003/AUDIT_20260916T224200Z_2ddf9b49748e/summary.json
Audit SHA256: 6ac3b1549164522087963e91fddd6cdc52ae6d05d985739af2298beda6f9e719
Protocol SHA256: fcc52bd378e7d76baa5baf9ee922b04939aaba668dafe6a1fca79eb3cda3bd33
Runner SHA256: 3098a144326df11ddf345d657e39188740a6296abb453f3a62a8fa47c4abf3c2


## 25. MOTIF-FUNC-004 — within-block sign-placement control

Status: INCONCLUSIVE; claim-ready: false.

The fixed-topology control preserved every edge coordinate, zero-weight
position, block-level sign multiset, and block-level absolute-weight multiset,
while permuting nonzero signs within each source-superclass to
destination-superclass block. The positive control passed 12/12. Both arms
were measured in all 12 seeds and all train/test liveness checks passed.

The paired observed-minus-block-sign-permuted routing-margin difference was
mean -0.029513888888888912, SD 0.057198328467371176, with 95% t interval
[-0.06585597296303776, 0.006828195185259938]. The predeclared interval gate
did not exclude zero.

Interpretation: this control provides no claim-ready evidence that the
observed within-block sign placement improves this locked LIF readout. It does
not show that sign placement is irrelevant, because the interval crosses zero.
The result does not establish biology, motif function, novelty, general
topology advantage, or ML transfer. M3 remains compatible with magnitude
placement or other within-block structure.

Artifact: research/results/MOTIF-FUNC-004/FULL_20260916T224521Z_2ddf9b49748e/summary.json
SHA256: 5e45322b6a811392aaf68451099fa50fef3607893d250f1af77671b0eb976fca
Independent audit: research/results/MOTIF-FUNC-004/AUDIT_20260916T224639Z_2ddf9b49748e/summary.json
Audit SHA256: 8ce8cd238a5d50c94f68c769570315ad3304f421c0dee78ac43027d5394aed5f
Protocol SHA256: 364e266b2148a028d78c71f9a9003ee48fdea403b48d8c23b98db0bc0092fa6e
Runner SHA256: a7343ab28ed9b0881afab67888b38548603ea3fc14518d50ab1e829016206302


## 26. MOTIF-FUNC-005 — within-block magnitude-placement control

Status: INCONCLUSIVE instrument-limited; claim-ready: false.

The fixed-topology control kept edge coordinates, zero positions, signs at
nonzero edges, block sign multisets, and block absolute-weight multisets fixed
while permuting absolute magnitudes within blocks. The positive control passed
12/12 and the observed arm was measured in 12/12. The magnitude-permuted arm
was MISSING in seeds [0, 3, 7, 8, 9] because independent rate calibration was
not accepted; these rows were not scored as negatives. The remaining 7 paired
rows were measured and their train/test liveness checks passed.

For those 7 pairs, observed-minus-magnitude-permuted margin was
0.11309523809523805, SD 0.0611629469912633, with 95% t interval
[0.05652894661576626, 0.16966152957470984]. Despite that interval, n=7 is
below the preregistered minimum of 8, so this ID cannot support a
magnitude-placement claim.

Artifact: research/results/MOTIF-FUNC-005/FULL_20260916T225003Z_2ddf9b49748e/summary.json
SHA256: 3d5e87e0ef2854865aeb3054dda031cfe7c1c65e665a8445c928ab0c07d9e200
Independent audit: research/results/MOTIF-FUNC-005/AUDIT_20260916T225122Z_2ddf9b49748e/summary.json
Audit SHA256: b429f4be0106ab1b82e64c9afe2cbb2007fb1c3523aebda54cb99e9b457f6f04
Protocol SHA256: e30ebc7be0de9c7617a3468254cc86f6f7c675bc0f3dc7df98d0a7f2e219aede
Runner SHA256: 8b4b3d725b16b5f89b3ee3f4fa7fa2b33fea2524a1b3e84c15ffec226267ec4f


## 27. MOTIF-FUNC-006 — one-time lower operating-point replication

Status: INCONCLUSIVE; claim-ready: false.

This preregistered single operating-point replication used target rate 0.003
to test whether M5 missingness was operating-point limited. The positive
control and observed arm were measured in 12/12 seeds. The
block-magnitude-permuted arm was measured in 8/12 and MISSING in seeds
[0, 1, 10, 11] because calibration was not accepted; missing rows were not
treated as negatives. All measured train/test liveness checks passed.

The 8 paired observed-minus-null margins had mean 0.08072916666666669, SD
0.13567397714888743, and 95% t interval
[-0.03269711675051455, 0.19415545008384794]. The interval crossed zero, so no
magnitude-placement claim is licensed. This closes the one-time
operating-point repair; no further target tuning is licensed for this branch.

Artifact: research/results/MOTIF-FUNC-006/FULL_20260916T225532Z_2ddf9b49748e/summary.json
SHA256: 4fc3d3479a4905269a87f2c119a51b5b6d76563ad52765ffb1d84202c4193d3b
Independent audit: research/results/MOTIF-FUNC-006/AUDIT_20260916T225701Z_2ddf9b49748e/summary.json
Audit SHA256: 8d3bec892c757d1c82b6aa0cae52202f46431a09e649bdcbaf20218e4a7474a5
Protocol SHA256: fa564b12b7a97fa2b427d5fa2492008578604a84949720be304f89acb53923eb
Runner SHA256: 609bdb76bcfe2d431d506597c5c8d0194498c349b0a792ec37c3be688b3f73b4


## 28. MOTIF-FUNC-007 — cross-stream-pair replication

Status: PASS for the predeclared locked readout; claim-ready only at this narrow
scope.

A new stream pair, A = cb_intrinsic and B = visual_centrifugal, was used with
the same fixed 500-node topology, weights, target rate, LIF task, calibration,
and train/test gates. The observed and global weight-permuted arms were
measured in all 12 seeds; positive control passed 12/12; all train/test
liveness checks passed. The null preserved topology, degrees, blocks,
reciprocity, edge count, and weight multiset.

The paired observed-minus-weight-permuted routing-margin difference was mean
0.2239583333333333, SD 0.06714142036241731, with 95% t interval
[0.18129871007072917, 0.2666179565959374]. The preregistered gate passed.

Interpretation: the M2 global weight-placement readout difference replicated
for this second stream pair. This supports limited cross-pair robustness of
the locked computational readout, not a biological mechanism, motif
attribution, novelty, general topology advantage, or ML transfer.

Artifact: research/results/MOTIF-FUNC-007/FULL_20260916T230250Z_2ddf9b49748e/summary.json
SHA256: d7e4dcd87a2c69779ff209120e1be761bbd33c7a0971fa3ecf1fcc16cd3e2f3d
Independent audit: research/results/MOTIF-FUNC-007/AUDIT_20260916T230420Z_2ddf9b49748e/summary.json
Audit SHA256: d18ac822dd25db61819cbc695299d6bc6351eae9bdfd3cb20ac65d47880747f6
Protocol SHA256: 2892c9244300742088c9e779d0ea1ee498d280c08facc71144ca30861fac81c4
Runner SHA256: a4507bb5db59554c17f85f853a463c864cd03fc68ed550d01607617c10c7afc7


## 29. MOTIF-FUNC-008 — second cross-stream-pair replication

Status: INCONCLUSIVE; claim-ready: false.

The predeclared pair A = visual_centrifugal and B = ol_intrinsic used the same
fixed topology, weights, target rate, LIF task, calibration, and train/test
gates as M2/M7. Observed and globally weight-permuted arms were measured in
12/12 seeds; the positive control passed 12/12; all train/test liveness checks
passed; and topology, degrees, blocks, reciprocity, edge count, and weight
multiset were preserved.

The paired observed-minus-weight-permuted routing-margin difference was mean
0.005208333333333333, SD 0.03985156328125154, with 95% t interval
[-0.02011214196831266, 0.030528808634979324]. The interval crossed zero.

Interpretation: this second new pair did not produce a claim-ready replication.
The combined evidence supports only limited task/pair-specific robustness of
the M2/M7 readout effect; it does not license universal, biological, motif,
novelty, general-topology, or ML-transfer claims.

Artifact: research/results/MOTIF-FUNC-008/FULL_20260916T230701Z_2ddf9b49748e/summary.json
SHA256: 20ed74b7b90e1e4ff9c3f93abc67f954ecb4043203ec64d77f1643b8ca211ed0
Independent audit: research/results/MOTIF-FUNC-008/AUDIT_20260916T230840Z_2ddf9b49748e/summary.json
Audit SHA256: 34b35e06ac44424a13be1c75f6bb980b5374abe2613370c4d43196aa806939c9
Protocol SHA256: 39213d2f413bf9c99b27805d284f6ace43b5c6b635c935c43aee28a4b9f93b3b
Runner SHA256: 0c1a781f96569544837184be65312127d9669dea47f6d8ad75b9f2cf8fd6db56
