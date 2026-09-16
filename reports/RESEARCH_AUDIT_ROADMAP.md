# Research audit + roadmap (A–L)

**Role:** research engineer, not PI. Inspection only except the three ledger/roadmap files and this report.  
**Repo:** `/home/ubuntu/fly-lab` · **Tip:** `0f08d20` (`cursor/anomaly-v2-real-sensor-f1ac`) · **main:** `11956c4`  
**When:** 2026-09-15/16 · **Box:** 2 vCPU / 15 GiB / no GPU · **pytest:** 58 passed in 4.94 s  
**Did not:** run new experiments, refactor, edit the anomaly detector, delete results, rewrite historical JSON, touch `data/raw/`.

Closed IDs stay closed. Valid sentence only: *the tested implementation/configuration did not demonstrate a topology advantage under that experimental setup.*

---

## A. What exists now

**VCS.** Git repo, no remotes. 18 commits from `ad1d670` (broken E1 preserved) to `0f08d20` (Anomaly V2). Working tree: no modified tracked files; untracked results include the **flagship** E1 ensemble JSON, polarity JSON, and `docs/ANOMALY_TOPOLOGY_ADVANTAGE.md`. No root README.

**Data.** `data/raw/` (~1.1 GB, gitignored, frozen MaleCNS v1.0). Derived graph ~247 MB gitignored: 165,122 neurons, 25,563,197 edges, Σw 124,025,046 (`graph_meta.json`). Polarity feather + policy JSON. NAB machine-temperature `.npy` + provenance under `data/derived/anomaly/` (~844 KB).

**Library.** `flylab/{graph,dynamics,nulls,spectral,polarity}.py` — sparse CSR/CSC/COO, LIF, degree-preserving null, weight perm, hub removal, spectral gain, named glutamate policies.

**E1 harness.** `experiments/harness/{e1_reservoir,positive_control,null_ensemble,gain_sweep,polarity_arms,ablations}.py`. PROTOCOL in `experiments/PROTOCOL.md`. Registry stale.

**Anomaly.** V1 synthetic EXP-001–006; V2 `--window` pipeline on one NAB series; adapters mostly stubs; default scorer threshold.

**Tests.** 58: leakage, liveness, nulls, spectral, polarity, controls, baselines, determinism, V2 pipeline. None cover EXP-001–006 science.

**Docs.** PROTOCOL, E1 audit report, portfolio brief, E1/Anomaly topology-advantage flags, V2 report, `PROJECT_STATE.json` (V2 engineering flags on this branch; `E1_TOPOLOGY_ADVANTAGE` present on `main`, omitted at tip).

**This pass added:** `RESEARCH_ROADMAP.md`, `RESEARCH_LEDGER.yaml`, `SCIENTIFIC_CLAIMS.md`, this file.

---

## B. What is scientifically complete

**Nothing that is a hypothesis about topology, memory, compute, or generalization.**

Complete enough to cite as *measurements with a protocol attached* (not as finished scientific conclusions):

- E0 counts from files (with documented delta vs published targets).
- Leak-closed dead-net at `syn_scale=0.002` → chance 0.2000 for connectome/ER/shuffle/MLP.
- Degree-preserving null properties on the E1 subgraph.
- Subgraph inhibition dominance and 60.05% UNKNOWN zeroing.
- PC-A/PC-B **at 450 probes / 0.01 / all-excitatory / 12×60** (pass) and PC-B **at 48 / 0.01 / 5×20** (fail).
- V2 engineering metrics on one NAB series with val-chosen threshold (not a connectome result).

`E1_TOPOLOGY_ADVANTAGE=FALSE` and `ANOMALY_TOPOLOGY_ADVANTAGE=FALSE` are **closed IDs**, not scientifically complete results (see D, F).

---

## C. What is engineering-complete

| Item | Complete? |
|---|---|
| SHA-256 lock + download scripts | Yes (raw not re-downloaded this pass) |
| Sparse graph on disk | Yes; **builder↔artifact provenance no** |
| LIF + spectral gain utilities | Yes |
| Degree-preserving / weight-perm / hub-drop in `flylab.nulls` + tests | Yes |
| `check_alive` implementation + unit tests | Yes; **not wired to claim runners** |
| PC harness | Yes; **not run at E1 config** |
| Anomaly V1 CLI `--demo` | Yes (synthetic) |
| Anomaly V2 `--window` + tests + measured JSON | **ENGINEERING TRUE** (`ANOMALY_V2_REAL_SENSOR`) |
| Camera/IMU/mic | Stubs |
| Git origin / root README / current registry | No |
| LSTM/GRU baseline | Deferred, no GPU |

Code existing ≠ milestone TRUE for science. V2 TRUE is engineering only.

---

## D. What hypotheses are closed

| ID | Closed as | Allowed statement |
|---|---|---|
| `E1_TOPOLOGY_ADVANTAGE` | Hypothesis ID (`docs/E1_TOPOLOGY_ADVANTAGE.md`) | Tested implementation/config did not demonstrate a topology advantage under that setup |
| `ANOMALY_TOPOLOGY_ADVANTAGE` / EXP-006 | Hypothesis ID; no EXP-007/008/009 topology hunt | Same sentence |

Do **not** close “biological topology has no value.” Do not rerun these IDs to rescue a win. Anomaly V2 is not a hypothesis; it is an engineering milestone — stop spending research budget on it.

---

## E. What hypotheses remain open

- Instrument sufficiency at 48 probes / rate 0.002 / signed (never measured).
- Protocol-valid connectome vs **degree-preserving** null on classification (**new ID** if done at all).
- Glutamate mapping effect on accuracy at PROTOCOL power (8×40 only).
- Memory capacity / delay (Track C).
- Compute per nonzero synapse (Track A) — `ops_proxy` still wrong.
- Continual learning, OOD-on-scientific-task, scaling with n (B, E, H).
- Architecture discovery, multimodal, embodiment (D, F, G) — open and **deferred**.
- Cross-connectome generalization (no second dataset).
- Derived-graph reproducibility from `scripts/build_graph.py`.

---

## F. What methodological problems were found

Prior audit items **verified against this tree** (not trusted blindly):

| Item | This pass |
|---|---|
| E1 probe leakage later closed | **Confirmed.** `probe_set` / `simulate_driven(..., input_ids=)`. |
| Silent reservoir at `syn_scale=0.002` | **Confirmed.** Leak-fixed JSON; config still 0.002. |
| No PC at 48 / 0.002 / signed | **Confirmed.** |
| Rate match once on seed 0 | **Confirmed.** Connectome seed 9: 306 spikes, acc 0.200, in the mean. |
| `check_alive` unused by new runners | **Confirmed.** Grep: harness `run_seed` + tests only. |
| EXP-006 test-label F1; `no_post_hoc_tuning: true` | **Confirmed.** FLAG; files not rewritten. V2 val-F1 does not fix EXP-006. |
| Glutamate UNKNOWN ~60% edges | **Confirmed** 14237/23708 subgraph edges. |
| No git origin | **Confirmed.** |
| `build_graph.py` reconstructed; `graph_meta` gitignored | **Confirmed.** Meta mtime 10:28; script 12:52; `.gitignore:5`. |

**Additional, still open:**

1. Flagship E1 and polarity JSONs **untracked**.
2. Mixing seed-CI vs draw-CI in prose tables.
3. MLP fitted on connectome features at connectome gain (readout ablation, not an independent baseline).
4. ER null confounds topology with sign balance, weight law, effective nnz (DP null does not).
5. `ops_proxy` counts explicit zeros (~2.50×).
6. `e1_config.json` has no `gain_normalization`.
7. Ensemble writes once at end (crash loses the run).
8. EXP-006 `hubs_removed` **bit-identical** to `fly_signed` (local rewrite zeros weights; tested `remove_topk_hubs` unused).
9. Anomaly arms at `gain=5`, not matched rate; `encode_to_current` z-scores each window.
10. EXP-005 “temporal hold-out” on i.i.d. copies of one template.
11. EXP-001–005 single seed; `er_null` `rng(0)` in `fly_scorer.py`.
12. `PROJECT_STATE.json` at tip dropped `E1_TOPOLOGY_ADVANTAGE`.
13. Registry stale (`e1_null_ensemble_powered: running`).
14. Powered E1 `provenance.git_rev` is write-time HEAD (`fe089d3`) while the process started earlier (known provenance footgun).

No new one-line documentation falsehood was rewritten. EXP-006 `no_post_hoc_tuning` is **flagged**.

---

## G. Current architecture of the repository

```
data/raw/ (immutable, gitignored) → scripts/build_graph.py
    → data/derived/graph/ (gitignored) + data/derived/neurons/
flylab/  graph, polarity, spectral, dynamics, nulls
experiments/harness/  E1 classification instrument
anomaly/  testbed app (V1 synthetic, V2 NAB window)
tests/    instrument unit tests + V2
docs/, reports/, experiments/PROTOCOL.md, PROJECT_STATE.json
```

Flow for E1: load subgraph (top-500 out-degree) → signed sparse W → LIF → 48 probes × 4 bins → ridge readout. Nulls: ER, degree-preserving, (coded) weight perm / hubs.  
Flow for V2: `.npy` → windows → threshold / rolling-z / OCSVM; optional fly ablation.

---

## H. What `RESEARCH_ROADMAP.md` now says

Phases 0–6 as required. Tracks A–H plus cross-connectome mapped; D/F/G and full-165k H deferred on this hardware, not deleted. Sequence: provenance → **instrument gate** → optional protocol-valid reservoir ID → Track C memory → A/B/H → Phase 3–6. Anomaly V2 gets no more research budget. Engineer notes: 8-track program too broad for this box; E1 gate before Track A; EXP-E1B-001 is a new ID not a rescue.

---

## I. The next 3 experiments

1. **EXP-INST-001** — Can PC-A/PC-B pass at 48 probes, rate 0.002, 12×60?
2. **EXP-E1B-001** — Under that gate + per-seed rate + `check_alive` + no-network control, does signed top-500 accuracy differ from the degree-preserving null? (New ID; two-sided; skip if PI forbids any new classification-vs-null run.)
3. **EXP-MEM-001** — Track C: delayed-classification / memory capacity vs DP, weight-perm, ring, ER at matched rate.

Details, compute, fail/success, roadmap branches: `RESEARCH_ROADMAP.md`.

---

## J. Why those 3 were selected

| Criterion | INST-001 | E1B-001 | MEM-001 |
|---|---|---|---|
| Scientific value | Unblocks or honestly blocks the whole program | Makes the closed E1 sentence evidence-bearing or replaces it | First ML-native connectome question |
| ML relevance | Instrument | Calibrates whether classification is the wrong task | Memory / CL / scaling |
| Falsifiable | Gate pass/fail | Two-sided vs DP | Acc(τ*) vs DP |
| Reproducible | Existing script + flags | After wiring liveness/rate | Same engine |
| Baselines | Ring vs ER | DP, perm, MLP, no-network | Ring, DP, perm |
| Compute | Minutes, 2 vCPU | ~0.5–1.5 h | ~1–3 h at n≤500 |
| Informs later | Everything | Whether to hunt classif. or move to C/A | Tracks B, D evaluator, H |

Not chosen: easiest (Anomaly already exists), flashy (embodiment), recruiter, or “make Fly win.” Not chosen: more NAB, EXP-006 rerun, Track D/F/G.

---

## K. What must NOT be worked on anymore

- EXP-006 / `ANOMALY_TOPOLOGY_ADVANTAGE` rescue; EXP-007/008/009 topology hunt.
- Further Anomaly V2 research (adapters-as-science, NAB scoreboard, fly-on-temperature as biology).
- Citing pre-fix 0.76 / `e1_pilot.json`.
- Overwriting results; rewriting historical JSON; silent conclusion edits.
- Touching `data/raw/`.
- Running `build_graph.py` into `data/derived/graph/` (clobber).
- Treating portfolio brief “publishable negative” as a claim.
- LSTM fakery; Doom/camera demos as evidence.
- Full-CNS powered runs on this 2 vCPU box.

---

## L. Inconsistencies between code, documentation, and scientific claims

| Claim / doc | Reality |
|---|---|
| `E1_TOPOLOGY_ADVANTAGE=FALSE` as finished science | Ungated config; seed-0 gain; dead seed 9; untracked JSON |
| “Rate-matched” (`docs/E1_TOPOLOGY_ADVANTAGE.md`, portfolio) | One match on seed 0; 100× rate spread |
| “PC-A and PC-B pass at 12×60” | True at 450 / 0.01 / all-ex; false as license for 48 / 0.002 / signed |
| `ANOMALY_TOPOLOGY_ADVANTAGE=FALSE` as science | Dead/quiet fly arm, 94× rate mismatch (prior live measure), no-op hubs, no gate |
| `no_post_hoc_tuning: true` in EXP-006 summary | F1 threshold on test labels via `summarize` |
| V2 `no_post_hoc_tuning: true` | **Holds for V2** (val max-F1 / train q95); do not conflate with EXP-006 |
| `PROTOCOL.md` PC must pass before connectome vs nulls | No runner imports `positive_control` |
| `PROTOCOL.md` ops_proxy nonzero only | `ops_proxy(W.nnz)` |
| `registry.json` ensemble running | Finished 13:04; polarity also done |
| `PROJECT_STATE.json` tip vs `main` | Tip is V2 engineering; main still has E1 FALSE + V1 mission |
| Portfolio “45 unit tests” / “publishable” | 58 tests; completeness fails |
| `build_graph.py` as the builder of record | On-disk meta schema ≠ script output; never re-run |
| EXP-006 “hubs” ablation | Identical AUROC vector to `fly_signed` |
| `ANOMALY_V2_REAL_SENSOR=true` as research progress | Engineering milestone only |

**Verdict:** the lab has a real instrument-repair history, a frozen connectome slice, and an engineering detector. It is **not** ready for Phase 2 claims, paper, or an 8-track parallel program on this box.

---

## Directory / size snapshot (raw contents not listed)

Repo sans `.git` / `.venv` / `data/raw` ≈ 250 MB derived + ~4 MB code/results. `data/raw` ~1.1 GB. Tests 58 passed. Hardware: 2 CPU, ~14 GiB available, no CUDA.
