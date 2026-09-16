# RESEARCH_ROADMAP.md

**Owner role of this document:** research-engineer audit, not PI decree.  
**Machine:** Ubuntu-1, 2 vCPU / 15 GiB RAM / no GPU.  
**Object of study:** the connectome (MaleCNS v1.0), not a product. Applications are testbeds.  
**Inspection base:** HEAD on branch cursor/exp-inst-001-c6ad; local commits only, no git origin.
**Companion files:** `RESEARCH_LEDGER.yaml`, `SCIENTIFIC_CLAIMS.md`, `reports/RESEARCH_AUDIT_ROADMAP.md`.

Do not assume Fly wins. Negative results count if the protocol is valid.  
`E1_TOPOLOGY_ADVANTAGE` and `ANOMALY_TOPOLOGY_ADVANTAGE` / EXP-006 are **CLOSED as hypothesis IDs**. The only allowed wording is: *the tested implementation/configuration did not demonstrate a topology advantage under that experimental setup.* That is **not** evidence that biological topology has no value. Do not rerun those IDs to rescue a win. Anomaly V2 is an engineering milestone — no further research budget.

**Current human-directed execution state (2026-09-16; supersedes earlier sequencing).** E1 and EXP-006 remain closed; EXP-E1B-001 is **DISABLED_BY_PI**. EXP-INST-001 reported PASS for constructed post-LIF feature injection only; it is not a topology result or a MEM gate. The pre-INST exploratory MEM pilot is preserved as **SUPERSEDED/INVALIDATED**, not confirmed or cited as memory evidence. EXP-MEM-001 and its one accuracy-blind mapping repair are **INVALIDATED** after required liveness failed; the historical checkpoint remains in WHERE_WE_STOPPED.md. EXP-MEM-002 remains INSTRUMENT_INCOMPLETE. EXP-MEM-003 is MEM_003_NO_PAIR after its primary map and one fallback map; no memory curve or EXP-A-001 is authorized. EXP-GLU-001 completed at 12 seeds with the preregistered comparison withheld. EXP-IGNITE-001 and the one authorized polarity sensitivity `EXP-IGNITE-002` completed smoke, sizing, and 12-seed confirm with NO_COIGNITE. N6 is DEFERRED_HARDWARE, N7 is documented as `QUEUED_2VCPU`, and N8 uses the existing bounded A2A queue; no further scientific ID is authorized by the handoff, and no unregistered branch is invented.

---

## Track map (A–H + cross-connectome)

Do not invent tracks. Do not drop tracks. Infeasible tracks stay on the map, deferred, with hardware named.

| Track | Name | Home phase | On this box? |
|---|---|---|---|
| A | Compute-optimal | Phase 1 (ops accounting) then Phase 2 | Yes at subgraph ≤500 after `ops_proxy` counts **nonzero** synapses only |
| B | Continual learning | Phase 2 | Small CPU experiments only after a valid task-specific memory protocol |
| C | Long-horizon memory | Phase 2 | Exploratory pilot authorized; confirm only after MEM controls and protocol freeze |
| D | Architecture discovery | Phase 2 late / extra hardware | **Defer:** NAS/search on 2 vCPU is not a serious search. Keep the track; do not fake it |
| E | Robustness / OOD | Phase 2 science + Phase 4 testbed | Yes for synthetic shift on CPU; **not** more Anomaly V2 |
| F | Multimodal fusion | Phase 4 | **Defer:** camera/IMU/mic are stubs; one NAB temperature series is not multimodal |
| G | Embodied / navigation | Phase 4 | **Defer:** no simulator, no GPU |
| H | Scaling laws | Phase 2 | Subgraph ladder n∈{128,256,500,1000,2000} on this box; **full 165k powered protocol not feasible** here |
| — | Cross-connectome generalization | Phase 3 | Needs another frozen connectome (download + RAM). Same CPU limits as H |

**Current sequencing (does not replace the 8-track program):** preserve closed E1/EXP-006 → fail-closed liveness is implemented and tested → MEM pilot is invalid due to a silent reservoir → audit input mapping/polarity and freeze an operating-point rule before any fresh, versioned pilot → freeze a complete protocol only after all controls and split-level liveness pass → consider confirmation only with adequate power. EXP-E1B-001 stays disabled. A/B/H follow only when their own prerequisites pass; D/F/G remain deferred until hardware/data exist.

---

# PHASE 0 — DATASET / INFRASTRUCTURE

### Objective
A frozen, hash-locked MaleCNS graph whose derived artifacts can be rebuilt from the script in git without silent overwrite, with named polarity policy, and with results actually tracked.

### Dependencies
- Never touch `data/raw/`.
- Existing feathers + `data/manifests/source.lock.json` (E0 hashes already verified on disk).

### Experiments
None. This phase is reconstruction, checksums, and bookkeeping.

Work items (not hypothesis hunts):

1. **Graph provenance.** `scripts/build_graph.py` was restored *after* `data/derived/graph/graph_meta.json` was written. Rebuild only to a **new** directory; compare n, nnz, Σw, sign counts, nnz-of-signed-zeros. Do not overwrite `data/derived/graph/`.
2. **Track or checksum the derived graph.** Today `data/derived/graph/` is gitignored (~247 MB). The read-only `scripts/verify_graph.py` now records checksums and validates it against `graph_meta`; the flagship E1 JSON is still **untracked**.
3. **Polarity policy named on every run.** Default `glutamate_unknown` zeroes 60.05% of E1-subgraph edges. That is a sensitivity axis, not a silent default for the only number.
4. **`ops_proxy`:** count executable structural nonzeros, not explicit zeros. `e1_reservoir.py` now records `stored_nnz` separately and uses `effective_nonzero_nnz(W)`. Required before Track A.
5. **Remote.** `git remote` is empty. Without origin, results are one disk failure from gone.
6. **Registry.** `experiments/registry.json` still lists the powered ensemble as `running`.

### Expected artifacts
- Checksums for derived CSR/CSC/COO + `graph_meta`.
- Rebuild-diff report (new out-dir vs current meta).
- `ops_proxy` definition matching `PROTOCOL.md` (nonzero only).
- Git remote or an explicit backup policy.
- Updated registry / this ledger.

### Scientific questions
- Does the restored builder reproduce the artifacts every E1 number depends on?
- What fraction of “connectome_signed” is glutamate-UNKNOWN zeroing vs true signed synapses?

### Completion criteria
- [ ] Rebuild in a side directory matches (or documents deltas vs) on-disk `n=165122`, `|E|=25563197`, Σw=124025046.
- [x] Derived graph has an independent checksum and read-only verifier (`reports/GRAPH_INTEGRITY.md`); default builder cannot clobber it, and the protected output guard is verified in `reports/BUILD_GRAPH_SAFETY.md`.
- [x] `ops_proxy` nonzero-only, tested (`reports/OPS_PROXY_AUDIT.md`).
- [ ] Powered E1 + polarity JSONs either tracked or checksummed in-repo.
- [ ] No claim depends on an untracked file.

### Risks
- Rebuild with `ground_truth`-preferring NT logic could change signs (prior audit: 0 disagreements on this snapshot — **re-verify**, do not assume).
- 247 MB graph + 1.1 GB raw on a 15 GiB box: extra copies must be temporary.
- No origin: collaboration and review are local-only.

---

# PHASE 1 — SCIENTIFIC BENCHMARK ENGINE

### Objective
An instrument that can fail closed: positive controls at the **measurement** configuration, liveness actually enforced, rate matched **per seed**, baselines that are baselines, CIs that are the same kind, results versioned and not overwritten.

This phase is the gate for Tracks A–H. It is **not** a topology-advantage hunt and **not** a rerun of EXP-006.

### Dependencies
Phase 0 checksums at least for the graph in use. Existing harness: `positive_control.py`, `null_ensemble.py`, `flylab/{nulls,spectral,dynamics}`.

### Experiments
- EXP-INST-001 is historical. Do not overwrite/re-run its ID; retain its limited post-LIF injection interpretation.
- Wire `check_alive()` into every runner that writes a claim-shaped JSON (`e1_reservoir`, `exp_inst_001`, `null_ensemble`, `polarity_arms`, MEM). Failed rows are retained and not scored as evidence.
- Per-seed `match_gain` + assert realised non-input rate within a pre-registered band (e.g. 2× of target).
- No-network linear readout and label-permutation floor in every classification table.
- Stop mixing `ci95` (seeds) with `ci95_over_draws` in one “± CI” column.
- Incremental write of ensemble rows (a crash at seed 11 currently loses the run).
- **Not in this phase:** Anomaly V2 polish; EXP-006 rescue; glutamate-powered 12×60 unless it is a named sensitivity after the gate.

### Expected artifacts
- `e1_positive_control_*` JSON at 48 / 0.002 / 12×60 (`gate_passed` true or false — both are results).
- Runner code paths that cannot score a silent reservoir as evidence (implementation is allowed *after* this roadmap freeze; not in this pass).
- PROTOCOL addendum: measurement config ≡ gate config, or an explicit documented residual.

### Scientific questions
- Can this readout resolve a known structural difference at the operating point used for E1?
- If not, is the limitation probes, rate, signed inhibition, or power?

### Completion criteria
- [ ] Historical EXP-INST-001 artifact remains immutable. Its reported gate is **not accepted** for future claims because seeds 5/9 failed feature guards but were marked alive. Stock PC-B was not run.
- [ ] Updated `check_alive`/runner fail-closed changes are verified by tests; only valid rows may contribute to claim metrics.
- [ ] Rate match is per seed; dead or >band seeds are not hidden in the mean. (EXP-INST-001 still used seed-0 match, E1 config; seed 9 rate 4e-5 kept.)
- [ ] No-network control present.
- [ ] PROTOCOL rules about gate, power, glutamate, ops_proxy, and versioned results are either enforced or explicitly waived with a reason.

### Risks
- PC-B at 48/0.002 may fail (the only 48-probe PC on disk already failed, at 0.01 and 5×20). That is a **successful** Phase 1 outcome if recorded — it blocks Phase 2, it does not license hunting Fly wins with a blinder instrument.
- Stock PC-B remains all-excitatory vs E1 signed/inhibition-dominated. Passing all-ex PC-B at 48/0.002 is necessary, not sufficient, for signed claims. A signed PC-B variant may be required; that is still Phase 1, still not topology-advantage.
- 2 vCPU: keep n=500, do not “just use 450 probes” as a sneak path unless that becomes the registered measurement config.

---

# PHASE 2 — CORE ML RESEARCH

### Objective
Ask ML-shaped questions of the **connectome**, with the Phase 1 instrument, without assuming a win: compute (A), continual learning (B), memory (C), architecture search (D), scaling (H). Robustness (E) as science belongs here too; robustness-as-product belongs in Phase 4.

### Dependencies
Phase 0 `ops_proxy` before Track A. EXP-E1B-001 remains disabled. EXP-MEM-001 has a separate pilot/control/freeze/confirm path; E1's 12×60 gate is not inherited.

### Experiments (track mapping)

| Order | Track | Experiment class | This box |
|---|---|---|---|
| 1 | C | **EXP-MEM-001** post-INST memory curve vs DP / weight-perm / ring / ER | INVALIDATED after one mapping repair; no interpretable curve |
| 2 | C | **EXP-MEM-002** liveness/rate instrument across all five arms | INSTRUMENT_INCOMPLETE after Q0 + one map 2; E1 hygiene committed |
| — | E1B | **EXP-E1B-001** | **DISABLED_BY_PI; do not run** |
| 3 | A | Bits or acc per nonzero synapse-step vs MLP/LSTM-CPU-tiny | after ops_proxy fix |
| 4 | B | Sequential task protocol, same subgraph, matched rate | small n |
| 5 | H | Subgraph size ladder; fit scaling of memory/acc vs n, nnz | n≤2000; not 165k powered |
| 6 | E | Shift in drive statistics / noise / class prior; not NAB | CPU yes |
| last | D | Search over readout / probe / subgraph / polarity — only with a cheap evaluator from C/H | **Defer heavy search** |

Ablations already coded but **not run** (`weight_permutation_null`, `remove_topk_hubs` in `flylab/nulls.py`) belong as controls inside EXP-E1B-001 / EXP-MEM-001, using the tested implementations, not local rewrites.

### Expected artifacts
Versioned JSON + a claims entry that can survive `SCIENTIFIC_CLAIMS.md` rules. No overwrite. Git-tracked.

### Scientific questions
- After a valid protocol, is there any CI-separated difference vs the **degree-preserving** null (the topology-only null)?
- Does topology show up in **memory** rather than in 64-step 5-way classification?
- Is any advantage (or cost) explained by hubness, signs, or weight law?
- How do metrics scale with n before anyone talks about the full CNS?

### Completion criteria
- [ ] At least one Track C or A result with PC passed at the same config, per-seed rate, liveness, strong baselines, 12×60 or a pre-registered power analysis.
- [ ] Track D not marked done because a script exists.
- [ ] Full-CNS scaling **not** claimed from n=500.

### Risks
- 2 vCPU / 15 GiB: n=165k LIF × 12 seeds × 60 trials is not a weekend job; do not schedule it here.
- LSTM/GRU still need GPU or a tiny CPU model explicitly labelled tiny.
- Re-using anomaly encoders that z-score away the signal (see audit §F).
- Quietly turning EXP-E1B-001 into “make Fly beat ER.” Failure criteria below forbid that.

---

# PHASE 3 — CROSS-CONNECTOME VALIDATION

### Objective
Any principle claimed on MaleCNS must be tested on at least one other frozen connectome (e.g. hemibrain, MANC, or a future public CNS) with the **same** protocol, not a new story per species.

### Dependencies
Phase 1 engine. A second dataset lockfile (SHA-256, license, never-touch raw). Do not start while E1-class measurements are still ungated.

### Experiments
- Repeat EXP-MEM-001 (and EXP-E1B-001 if still informative) on connectome 2.
- Negative transfer: train readout or hyperparameters on MaleCNS subgraph, evaluate on the other (and reverse).
- Shared null recipe: degree-preserving + weight permutation + |V|,|E| ER with **matched weight law**, not 50/50 ±uniform.

### Expected artifacts
Second `source.lock.json`, derived graph meta, matched-protocol JSON.

### Scientific questions
- Is any effect MaleCNS-specific (sex, taxon, subgraph rule) or protocol-specific?
- Do scaling curves (H) overlay in reduced units (nnz, mean degree, spectral radius)?

### Completion criteria
- [ ] Two locked connectomes, same instrument config, pre-registered metrics.
- [ ] Cross-connectome claim has a CI and a null, or is labelled anecdote.

### Risks
- Download size vs disk; second 165k-class graph may not fit two copies + raw on this VM.
- Different reconstruction conventions (proofread vs Traced) — document, do not force counts.
- This box may be too small; say so and wait for hardware rather than downsampling silently.

---

# PHASE 4 — APPLICATION TESTBEDS

### Objective
Use applications to **stress** principles from Phase 2–3, not to prove the fly is a product. Anomaly detection is one testbed and is **done as a research line** for now.

### Dependencies
A valid instrument. Tracks E and F need tasks that are not label-leaky and not ceiling-easy (EXP-001 was ceiling).

### Experiments
| Track | Testbed | Status on this box |
|---|---|---|
| E | Robustness/OOD: distribution shift on the scientific task (drive noise, template shift, held-out classes) | Feasible |
| F | Multimodal fusion | **Deferred** — stubs only; V2 is unimodal temperature |
| G | Embodied/navigation | **Deferred** — no env, no GPU |
| (closed) | Anomaly V1/V2 | Engineering milestone. **No more research budget.** Camera/IMU/mic not a science goal. |

### Expected artifacts
Testbed protocol + baselines stronger than the testbed’s own naive threshold when that threshold already wins (it did on EXP-006 and on NAB temperature).

### Scientific questions
- Does a memory or compute advantage from Phase 2 show up when the task is not 5-way phase classification?
- Where do classical baselines dominate, honestly?

### Completion criteria
- [ ] Each testbed has a frozen split, a baseline that can win, and a connectome arm that can fail.
- [ ] No testbed result is used as a topology-advantage reopen.

### Risks
- Recreating EXP-006 defects (test-tuned F1, dead reservoir, gain≠rate, no-op hub ablation).
- Recruiter demos (Doom, live camera) substituting for evidence — PROTOCOL already forbids this.

---

# PHASE 5 — AUTONOMOUS RESEARCH LOOP

### Objective
A loop that proposes experiments, runs only those that pass Phase 1 gates, writes versioned JSON, and updates `SCIENTIFIC_CLAIMS.md` **without** flipping CLOSED IDs or inventing wins.

### Dependencies
Phases 0–1. Human (PI) still owns CLOSED IDs and hardware upgrades.

### Experiments
Meta: can a runner refuse to start if PC is stale, `check_alive` is skipped, or `no_post_hoc_tuning` would be a lie?

### Expected artifacts
Job queue + claim linter (CI that fails if a result JSON lacks `task_validity` / provenance / git rev).

### Scientific questions
- Which hypotheses are actually open after EXP-MEM-001?
- Where does the loop waste the 2 vCPU budget (known failure mode: Anomaly V1 in ~10 minutes with no tests)?

### Completion criteria
- [ ] A new experiment cannot write `*_ADVANTAGE: true/false` without PROTOCOL fields.
- [ ] CLOSED IDs are write-protected in the ledger.

### Risks
- Autonomous loop on 2 vCPU becomes a random search (Track D without an evaluator).
- Agents rewriting historical JSON (forbidden).

---

# PHASE 6 — PAPER / OPEN-SOURCE RELEASE

### Objective
A paper and a repo someone else can rerun: data locks, builder, tests, honest negatives, no origin-shaped hole.

### Dependencies
At least: Phase 0 provenance, Phase 1 gate, one scientifically complete experiment (likely EXP-E1B-001 or EXP-MEM-001). Not “V2 TRUE.”

### Experiments
Reproduction by a second machine. Not a new hypothesis.

### Expected artifacts
- Public git origin.
- README (none at repo root today).
- Data card: MaleCNS CC-BY + NAB MIT subset if V2 is mentioned as engineering.
- Paper-shaped claims that match `SCIENTIFIC_CLAIMS.md`.

### Scientific questions
- What can be stated in the abstract without the 20:00 audit tearing it down?

### Completion criteria
- [ ] Origin exists; `graph_meta` rebuildable or checksummed.
- [ ] Every number in the paper has a protocol and a file.
- [ ] CLOSED IDs use the valid sentence, not “biology failed.”
- [ ] 8 tracks are reported as a **program**, with D/F/G explicitly deferred, not as completed results.

### Risks
- Portfolio brief already overclaims (“publishable negative”). Do not ship that text.
- Mixing V2 engineering metrics into a connectome paper.

---

# Next three experiments

Selected by: scientific value, ML relevance, falsifiability, reproducibility, baseline strength, compute on **2 vCPU / 15 GiB**, publishable evidence, information for later work.  
Not selected by: ease, flash, recruiter, making Fly win.

---

## EXP-INST-001 — Positive-control gate at the E1 measurement config

**Question.** Can PC-A (activity) and PC-B (structure: ring vs ER) separate at **48 probes**, **target non-input rate 0.002**, **12 seeds × 60 trials/class** — the operating point of the powered E1 run?

**Hypothesis (instrument, not MaleCNS).** If the E1 readout is a valid structure sensor at that config, PC-B |Δacc| ≥ 0.10 with 95% CI excluding 0, and PC-A likewise. If not, the instrument is insufficient at that config.

**Why it matters.** The only passing gate on disk is **450 probes / rate 0.01 / all-excitatory**. The only 48-probe gate **failed** (rate 0.01, 5×20). E1 was scored at 48 / 0.002 / signed. Every later track that uses this reservoir inherits that hole. This is the highest-information experiment in the program. It does not reopen EXP-006.

**Required infrastructure.** Existing `experiments/harness/positive_control.py` (`--n-probes 48 --target-rate 0.002 --seeds 0-11 --n-trials 60`). Graph on disk. No `data/raw/` access. Record residual: stock PC-B is still all-excitatory.

**Baselines.** Ring vs ER *is* the contrast. No MLP required.

**Controls.** Same n, |E|, weight law, all-excitatory both arms (as coded); per-graph rate bisection; paired seeds; `MIN_EFFECT = 0.10`. Do not lower seeds/trials to pass.

**Metrics.** Paired Δacc, CI95, `separated`, `gate_passed`, realised rates, `rate_match_spread`.

**Expected compute.** Minutes to ~20 min on this box (450-probe 12×60 already ran here). 2 vCPU sufficient. No GPU.

**Failure criteria.** PC-B not separated; rate spread that drowns the contrast; crash with no JSON. **A failed gate is not a scientific failure of the connectome.**

**Success criteria.** Both PCs pass at this config **or** a written instrument-insufficient decision that blocks Phase 2.

**Recorded outcome (2026-09-16, `3dbe1d9`; historical artifact preserved).** The file reports constructed-effect PASS. Audit found seeds 5 and 9 have `dead_reason` but `alive=true`; the aggregator admitted both. Corrected validity therefore rejects the legacy gate for future claims. The positive arm also saturates at accuracy 1.0 and injects signal after LIF, so it demonstrates only a limited feature-space response. Stock PC-B was not run. Do not repeat/overwrite this ID or use it to launch E1B/MEM confirmation.

**What would change the roadmap.**  
- **Fail:** Phase 2 frozen. Redesign readout (probes, features, n, timescale) before Tracks A–H. Do not interpret E1’s 0.63 vs 0.65.  
- **Pass:** EXP-E1B-001 unblocked *as a later decision*. Existing E1 numbers become *more* interpretable, still not complete (seed-0 gain, no `check_alive` on the ensemble runner, seed 9 still in the mean). This INST-001 run **stops** and does not start E1B.  
- **Pass all-ex but later signed PC-B fails:** signed E1 stays incomplete; do not treat all-ex PC as licensing signed claims. (Not applicable: all-ex PC-B was not the test used here.)

---

## EXP-E1B-001 — Protocol-valid reservoir comparison (new ID; disabled)

**State:** `DISABLED_BY_PI`. Do not execute. The historical plan below is retained for audit context only; EXP-INST-001's reported PASS does not authorize it.

**Question.** Under a frozen valid protocol (EXP-INST-001 passed, per-seed rate match, `check_alive`, no-network control, nonzero `ops_proxy`, named glutamate policy), does signed MaleCNS top-500 linear-readout accuracy exceed the **degree-preserving** null (primary) and a weight-law-matched ER (secondary) on held-out temporal classification?

**Hypothesis.** Two-sided. We do **not** hypothesize that Fly wins. Either CI-separated superiority vs DP, or a valid tie/loss, is a result. This is **not** EXP-006, **not** `ANOMALY_TOPOLOGY_ADVANTAGE`, **not** a rescue of `E1_TOPOLOGY_ADVANTAGE`. If the PI forbids any new connectome-vs-null accuracy run, skip this ID and go to EXP-MEM-001 after EXP-INST-001 only — see Engineer notes.

**Why it matters.** The closed E1 ID is not scientifically complete. The field (and this lab) cannot use “no topology advantage” as a Phase 2 prior until one measurement can survive the audit. ML relevance: it calibrates whether 64-step classification is even the right task (if valid-negative, Track C/A become more important than another classifier).

**Required infrastructure.** Phase 1 wiring (liveness, per-seed gain, incremental JSON write). Use `flylab.nulls.degree_preserving_null` and `weight_permutation_null`, not local copies. Track the result file.

**Baselines.** Degree-preserving (primary topology null); weight permutation (topology fixed); `|w|`; ER with documented confounds or a weight-law-matched ER; budget-matched MLP (±10% readout params); **no-network** readout on raw drive; label-permutation floor. Ridge sweep on train-only.

**Controls.** 12×60; ≥20 null draws; null RNG ≠ task seeds; glutamate policy named; dead seeds in a `task_validity` block, excluded from the primary mean with a pre-registered rule; same probes across arms.

**Metrics.** Accuracy mean ± 95% CI **over seeds for every arm**; paired diffs vs DP and vs weight-perm; realised rates; liveness; nonzero ops.

**Expected compute.** Historical powered run was 779 s without per-seed bisection. Budget **30–90 min** CPU. Fits 15 GiB at n=500. No GPU. If per-seed matching explodes past ~2 h, cut null draws first, not seeds.

**Failure criteria.** Starting without EXP-INST-001 pass; averaging dead seeds; matching gain only on seed 0 again; mixing CI kinds; untracked JSON; test-set ridge; claiming advantage vs ER only.

**Success criteria (protocol).** All controls executed and git-tracked.  
**Success criteria (science).** A CI that does or does not exclude 0 vs **DP**. Either sign is publishable *if* the protocol held.

**What would change the roadmap.**  
- **Valid negative vs DP:** do not hunt classification wins; put budget on EXP-MEM-001 and Track A. Closed E1 sentence becomes evidence-bearing for this implementation/config.  
- **Valid positive vs DP:** open a **new** hypothesis ID about *where* (delay, motifs, hubs) — still not “Fly wins” and still not EXP-006.  
- **Many dead seeds after per-seed match:** dynamics/subgraph/polarity problem; Track D stays deferred; debug ignition, don’t add tasks.

---

## EXP-MEM-001 — Long-horizon memory (Track C)

**Question (explicit).** With one binary cue at t=0, zero input during the delay, and a final-step non-input readout, how does recall accuracy vary with lag? Compare the curve with degree-preserving (primary topology null), fixed-topology weight permutation, ring and ER controls, and CPU-tiny LSTM/GRU/Transformer/sparse-RNN baselines at measured parameter budgets. A ring need not beat ER; that comparison is descriptive, not a validity gate.

**Hypothesis.** Two-sided. A CI-separated advantage, tie, or loss vs DP is interpretable only if the frozen controls and all planned seeds pass. The FIFO delay line is a software/task positive control, not a neural memory result.

**Why it matters.** Memory is the ML property native to recurrent connectomes. It informs Track B (continual learning) and Track H (does capacity scale with n or only with rate?). It is not an application testbed and not Anomaly V2.

**Required infrastructure.** MEM-specific positive and negative controls; fail-closed liveness; leakage checks; measured per-seed operating rates; frozen train/validation/test split and lag grid. n≤500. No EXP-INST-001 pass is inherited. LSTM/GRU/Transformer: CPU-tiny if measured feasible, otherwise explicitly deferred; no substitute model described as those architectures.

**Baselines.** ML: LSTM, GRU, small Transformer, sparse RNN (matched budget, CPU-tiny or deferred). Structural controls: ring lattice (PC), DP null, weight permutation, ER (confounded unless weight-matched). Optional tiny linear / echo-state with the same readout budget.

**Controls.** Delay is the independent variable; disclose rate-matching procedure and native rates. Same graph size/edge count where the control permits; exclude inputs from probes; independent generated train and test trials; tune readout on training data only; keep all failed seeds visible. Freeze sample size using pilot-only variance and a stated power target. No E1 seed count/gain/effect threshold transfers automatically.

**Metrics.** Memory curve Acc(τ) ± CI; memory capacity summary; realised rates; liveness. Primary: paired Δacc at pre-registered τ*.

**Compute.** Not yet known. Measure wall time, CPU time and memory on the small pilot, then size the frozen run. Do not label a projected runtime as a measurement.

**Failure criteria.** Cue reaches the readout directly; later external input is nonzero; positive FIFO control fails; memoryless negative control shows above-chance recall; required seed/arm fails liveness; metrics use non-terminal bins; or confirmatory parameters change after test inspection.

**Success criteria.** Task plumbing controls pass and all planned measurements are valid. A resolved connectome-vs-DP difference of either sign is a scientific result; a wide interval is inconclusive, not equivalence. Ring-vs-ER outcome is reported but never required to pass.

**What would change the roadmap.**  
- **Connectome > DP on memory:** prioritize B and H; Track D can use memory as cheap evaluator; Phase 4 testbeds may use delay tasks.  
- **Connectome ≈ DP:** do not claim structure helps memory; Track A becomes “does any sparse recurrence beat MLP per op?”, not uniqueness of MaleCNS.  
- **Connectome < DP:** document; inspect inhibition-dominance and glutamate zeros before any architecture search (D).

---

# Engineer notes / disagreements

I am not the PI. I do not replace the 8-track program with a smaller one. I sequence it.

1. **This 8-track program is too broad for 2 vCPU / 15 GiB / no GPU** if treated as parallel science. Tracks D, F, and G cannot be executed seriously here (NAS; real multimodal sensors; embodiment). They stay on the map as deferred, not deleted. Track H at full 165k is not feasible on this box. Claiming otherwise would be a documentation falsehood.

2. **The E1 / EXP-006 FALSE flags are not scientifically complete.** Closing the IDs is correct (do not rescue). Treating them as a prior that “topology doesn’t help, proceed to applications” is incorrect. **EXP-INST-001 must happen before Track A.** Compute-optimal numbers on a dead or ungated reservoir are not compute-optimal.

3. **Anomaly V2 should not consume more research budget.** Agreed with the PI stance. V2 is ENGINEERING TRUE for one NAB series. Fly-on-NAB AUROC 0.43 is not a topology result.

4. **EXP-E1B-001 is the disagreement-prone item.** It looks like rerunning E1. It is a **new ID** with controls the closed run lacked. If the PI forbids any new connectome-vs-null **classification** measurement, drop EXP-E1B-001 and run EXP-MEM-001 immediately after EXP-INST-001. Do not drop the PC gate.

5. **Do not start Track A until `ops_proxy` stops counting explicit zeros** (~2.5× inflation on the signed subgraph). That is Phase 0/1, not a new advantage claim.

6. **ER is not a topology-only null** in this codebase (50/50 signs, uniform weights, no UNKNOWN zeros). Degree-preserving + weight permutation are the honest pair. Portfolio tables that put ER and DP in one column as equivalent nulls should not be reused.

7. **No git origin** is an infrastructure emergency for a research program, not a style issue.

---

## Prior independent-audit items (verified this pass)

| Item | Verdict |
|---|---|
| E1 probe leakage later closed | **Confirmed.** `input_ids` passed; probes from non-input pool; leak-fixed run at chance. |
| Reservoir silent at `syn_scale=0.002` | **Confirmed.** Leak-fixed JSON; `e1_config.json` still ships 0.002. |
| No PC at 48 / 0.002 / signed | **Confirmed.** Pass = 450 / 0.01 / all-ex; 48-probe = 0.01 and FAIL. |
| Rate match once on seed 0 | **Confirmed.** `null_ensemble.py`; seed 9 dead in the mean. |
| `check_alive` never called by new runners | **Confirmed.** Grep: `e1_reservoir.py` + tests only. |
| EXP-006 test-label F1 + false `no_post_hoc_tuning` | **Confirmed.** FLAG only; historical files not rewritten. V2 val-split does not retroactively fix EXP-006. |
| Glutamate UNKNOWN zeros ~60% of edges | **Confirmed** on E1 subgraph (14,237/23,708). Full-graph **neuron** U=33,439/165,122 is a different statistic. |
| No git origin | **Confirmed.** |
| `build_graph.py` reconstructed; `graph_meta` gitignored | **Confirmed.** Artifacts older than restored script; `.gitignore:5`. |

---

## ROUTING-002 — calibration envelope complete

ROUTING-002 was preregistered and run as a calibration-only experiment. On the
fixed nine-point gain grid and 12 seeds, the reference target 0.002 ±15% was
reachable in 0/12 connectome, 1/12 degree-preserving, and 5/12
block-preserving seeds. No task metric was computed.

Decision: ROUTING-001 remains INCONCLUSIVE and is not repaired or rewritten.
A new operating point may be tested only in ROUTING-003, whose protocol must be
frozen before task metrics. No claim about biological routing or ML transfer is
licensed by the calibration result.

---

## ROUTING-003 — operating-point replication complete

ROUTING-003 tested a new target rate of 0.013 ±15%, selected from the
ROUTING-002 calibration envelope and frozen before task metrics. The positive
control passed 12/12; connectome and degree controls were measured 12/12; the
block-preserving arm was measured 8/12 because four seeds did not calibrate at
the target. The paired n=8 contrast was -0.07031250000000004 with CI95
[-0.14872401153071557, 0.008099011530715503]. Classification: INCONCLUSIVE.

Decision: do not call this a routing negative or positive, and do not launch an
ML abstraction. Pivot to a preregistered higher-order motif inventory with
degree-preserving nulls, keeping the result structural.

---

## MOTIF-MINE-001 — structural candidate

The fixed 500-node subgraph contained 85 directed 3-cycles and 62,611
non-induced feed-forward occurrences. Across 20 degree-preserving nulls, the
cycle mean was 84.85 ±0.3663 and the feed-forward mean was 25,254.5 ±237.19.
This is a structural enrichment screen, not a biological or ML result.

The large feed-forward delta may reflect higher-order closure beyond in/out
degree, but it may also reflect reciprocal structure, module/block structure,
or other unpreserved dependencies. MOTIF-MINE-002 is preregistered to test a
block-preserving degree-matched null before any functional translation.

---

## MOTIF-MINE-002 — block-preserving control complete

The feed-forward enrichment persisted after preserving directed degrees and
superclass source-to-destination blocks: observed 62,611 versus 36,682.15
±280.39 across 20 nulls. Directed 3-cycles remained near-null. This narrows,
but does not remove, the alternatives of reciprocal structure, non-induced
counting, spatial organization, and high-out-degree selection. MOTIF-MINE-003
will use an induced motif definition with both degree and block controls.

---

## Motif cycle-count audit correction

A smoke consistency check found that the historical cycle helper in
MOTIF-MINE-001/002 used boolean sparse multiplication. Those cycle submetrics
are invalidated and removed from claims; the historical FFL counts remain
unaffected. MOTIF-MINE-003 uses explicit induced-cycle enumeration and is the
first valid cycle-control measurement in this chain.

---

## MOTIF-MINE-003 — induced control complete

The non-induced FFL signal did not survive reciprocal-edge exclusion. Observed
induced FFLs were 15,740 versus 18,953.1 ±266.998 in degree nulls and
22,673.05 ±383.731 in block nulls. Induced cycles were also lower than both
null families. The feed-forward primitive is therefore not accepted as a
breakthrough candidate under this control. The next mechanism screen tests
whether signed polarity composition, rather than motif abundance, is
structured.

---

## Motif edge-presence audit correction

The first three motif IDs are invalidated as full-topology analyses because
their binary adjacency was derived from signed weights and dropped UNKNOWN
zero-weight edges. Their files remain immutable history. No FFL or cycle number
from those IDs is used going forward. MOTIF-MINE-004 repeats the question on
the unsigned edge topology with induced and non-induced definitions.



## MOTIF-MINE-004 — corrected unsigned topology

The corrected unsigned-edge run is complete on the fixed 500-node subgraph:
23,704 analyzed edges after removing 4 self-loops, 20 degree nulls, 20 block
nulls, and zero invariant failures. Non-induced FFLs were 490,588 versus null
means 250,756.2 and 351,624.5. Induced FFLs were 72,245 versus 142,679.65 and
133,260.15; induced cycles were 4,276 versus 32,600.2 and 22,528.65.

Decision: record a mixed structural signature only. Do not translate it into
function or ML architecture. The next discriminating experiment is
SPECIALIZATION-001, which tests signed composition of induced FFLs under the
same null families.


## Audit correction: MOTIF-MINE-004 induced counter

MOTIF-MINE-004 omitted the sink-to-middle reverse-edge exclusion in its induced
FFL counter. Its induced submetrics are invalidated; its non-induced count is
not affected. MOTIF-MINE-005 is preregistered with the explicit three-edge
induced condition before any new metrics.


## MOTIF-MINE-005 — corrected result

The corrected induced count is 33,551, not M4's invalid 72,245. It is below
both degree and block null means; induced cycles are likewise depleted. The
non-induced FFL count remains enriched, consistent with a reciprocal/extra-edge
explanation. SPECIALIZATION-001's independent induced total matches 33,551.

Decision: no computational or biological primitive is established. The next
structural discriminator should preserve reciprocity in addition to degree and
superclass blocks.


## MOTIF-MINE-006B — efficient reciprocity control

The first M6 swap generator preserved correctness only after a guard but its
smoke exceeded ten minutes, projecting near the operational time gate. It was
stopped before metrics. M6B preregisters endpoint permutations within compatible
superclass groups, retaining the same degree/block/reciprocity target with a
bounded 20-round construction. No M6 result is claimable.


## MOTIF-MINE-007 — degree plus reciprocity complement

The block-preserving endpoint null was mostly rigid in smoke and is not a
strong evidence control. M7 intentionally drops block preservation while
retaining exact node degrees and reciprocal-pair count, making a complementary
null with useful mixing. Results remain pending.


## MOTIF-MINE-007B — reciprocity complement complete

The global degree+reciprocity null completed 20/20 with exact swaps and
invariants. Non-induced FFLs remained above its mean (490,588 vs 240,957.95);
induced FFLs were also above it (33,551 vs 23,621.65), while induced cycles
were near it. Because blocks were intentionally broken, this result narrows
but does not identify the mechanism. Move to a functional signed-weight test
before any architecture or novelty claim.


## MOTIF-FUNC-001 — narrow functional PASS

The locked LIF readout separated the observed signed graph from the
degree+reciprocity null: 11 paired seeds, mean margin difference 0.17614,
95% t interval [0.14789, 0.20438], positive control 12/12. This is not
motif attribution because the null breaks superclass blocks. The next control
keeps topology fixed and permutes weights to test whether weight placement,
rather than topology, drives the readout.


## MOTIF-FUNC-002 — fixed-topology weight placement control

The preregistered 12-seed readout completed with all observed and
weight-permuted arms measured and all train/test liveness checks alive. The
observed assignment exceeded the global weight permutation by mean margin
0.12847222222222224, 95% t interval [0.08783645362404835, 0.16910799082039613].
This narrows the M1 signal to a dependence on where the signed weights sit on
this fixed topology, but it is not motif, biological, novelty, or ML evidence.
A wording audit corrected the record count: 23,708 selected records preceded
removal of 4 self-loops, leaving 23,704 analyzed records. Next is a
block-preserving weight permutation to test whether coarse block allocation
explains the effect.


## MOTIF-FUNC-003 — within-block weight placement control

The preregistered 12-seed control fixed topology and preserved each
source-superclass to destination-superclass weight multiset while permuting
weights within blocks. Both arms were measured in all seeds, liveness passed,
and the observed-minus-null margin was 0.12847222222222224 with 95% t interval
[0.08232979134020302, 0.17461465310424146]. Thus coarse block weight
composition alone did not account for the result in this locked readout.
This remains functional evidence for a computational control only; it is not
motif, biological, novelty, or ML-transfer evidence. Next: a pre-registered
sign-versus-magnitude placement control.


## MOTIF-FUNC-004 — within-block sign placement control

The preregistered 12-seed control preserved topology, zero positions, block sign
counts, and block absolute-weight multisets while permuting signs within blocks.
All arms were measured and alive, but observed-minus-null was
-0.029513888888888912 with 95% t interval
[-0.06585597296303776, 0.006828195185259938]. Classification: INCONCLUSIVE.
This is not evidence that polarity is irrelevant; it leaves magnitude placement
and other within-block structure unresolved. Next: magnitude-placement control.


## MOTIF-FUNC-005 — within-block magnitude placement control

The full control preserved topology, signs, zero positions, and block
distributions, but the magnitude-permuted arm calibrated in only 7/12 seeds;
five rows were MISSING, not negatives. The 7-pair observed-minus-null mean was
0.11309523809523805 with 95% t interval
[0.05652894661576626, 0.16966152957470984], but the preregistered n≥8 gate
failed. Classification: INCONCLUSIVE instrument-limited. A single new
operating-point replication is the next diagnostic; no indefinite tuning.


## MOTIF-FUNC-006 — one-time lower operating-point replication

The lower target 0.003 recovered 8/12 magnitude-arm pairs, with four rows
MISSING rather than negative. The paired mean was 0.08072916666666669, but
the 95% t interval [-0.03269711675051455, 0.19415545008384794] crossed zero.
Classification: INCONCLUSIVE. This closes target tuning for the magnitude
branch. Next is an independent stream-pair replication of the narrow M2/M3
readout effect.


## MOTIF-FUNC-007 — cross-stream-pair replication

The predeclared pair cb_intrinsic + visual_centrifugal replicated M2 with
12/12 measured observed and permuted arms, positive control 12/12, and live
train/test splits. Observed-minus-null mean was 0.2239583333333333 with 95% t
interval [0.18129871007072917, 0.2666179565959374]. This strengthens the
narrow readout result across one new pair but does not establish biology,
motifs, novelty, or ML transfer. A second cross-stream pair is next.


## MOTIF-FUNC-008 — second cross-stream-pair replication

The second new pair visual_centrifugal + ol_intrinsic had complete measurement
and liveness, but observed-minus-null was 0.005208333333333333 with 95% t
interval [-0.02011214196831266, 0.030528808634979324]. Classification:
INCONCLUSIVE. Together with M2/M7, this limits the result to selected
task/pair conditions. Publish the reproducible artifacts with these negative
and incomplete controls visible.
