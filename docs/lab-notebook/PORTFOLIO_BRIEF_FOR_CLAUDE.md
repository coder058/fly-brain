# Fly Lab — Portfolio Brief (for Claude / resume use)

**Audience:** Claude (or any assistant) drafting portfolio entries, CV bullets, or case studies.  
**Tone required:** technical, honest, no hype. Do **not** claim that the fly connectome beat strong nulls or that “neuromorphic AGI” was achieved.  
**Last updated:** 2026-09-15  
**Repo host:** AWS Lightsail Ubuntu-1 (`~/fly-lab`), commit tip around `fe089d3`  
**Data:** MaleCNS v1.0 (Janelia), CC-BY — frozen raw files with verified SHA-256

---

## One-line pitch (safe)

Built a reproducible research lab that turns the *Drosophila* MaleCNS v1.0 connectome into a sparse computational graph, with audited reservoir experiments, positive-control gates, and powered null ensembles — and published an honest **negative** on the first topology claim after fixing label-leakage bugs that had produced false “null-like” scores.

---

## What the project is

**Fly Lab** is an experimental compute platform to ask:

> Can the connectivity of a complete biological CNS be used as a learnable / generalizable computational architecture — and can we extract principles that beat strong baselines?

It is **not** a Doom demo, a visualization, or an API wrapper. The working principle: *spectacular demos ≠ evidence*. Evidence = reproducible metrics vs strong baselines + ablations + efficiency proxies, with gates that can fail closed.

---

## Stack & infra

| Layer | Choices |
|---|---|
| Language | Python 3.12, pinned `requirements.txt` |
| Data | PyArrow feathers (MaleCNS flat connectome) |
| Graph | SciPy sparse CSR/CSC/COO — never dense \(N\times N\) |
| Dynamics | LIF (CPU), signed E/I/UNKNOWN weights |
| Experiments | Custom harness (`experiments/harness/*`) |
| Stats | Multi-seed means ± 95% CI; null ensembles with decoupled RNG |
| Compute | AWS Lightsail memory-optimized **16 GB / 2 vCPU** (no GPU) |
| VCS | Git on Lightsail; versioned results (`<prefix>_<UTC>_<gitrev>.json`) |

**Graph derived (Traced↔Traced filter):**  
165,122 neurons · 25,563,197 directed edges · Σ weights ≈ 124,025,046 synaptic contacts  
(Published validation targets ~166.7k / ~25.58M differ by &lt;1% — documented, not forced.)

---

## Progress analysis (what actually happened)

### Phase A — Data & infra (done)

1. Robust download + SHA-256 lock for official MaleCNS v1.0 feathers.  
2. Diagnosis: raw edge table (~152M rows) includes non-annotated partners; **Traced∩Traced** recovers the intended scale.  
3. Sparse signed graph + neuron table + polarity join.  
4. Hardware profile: CPU-only path; Lightsail sized for RAM not GPU.

### Phase B — False start on E1 (invalid — do not cite as science)

Early “connectome ≈ ER ≈ shuffle ≈ 0.76, MLP ≈ 0.87” numbers were **not** a topology result. Independent line-by-line audit found:

- Probe / readout leakage: driven input neurons entered features → label leak.  
- Dead non-input reservoir at the configured gain; liveness guard only checked feature variance (defeated by the leak).  
- Degree “shuffle” destroyed ~8% of edges via silent COO duplicate summing — not degree-preserving.  
- Arms compared at wildly different effective gains (ρ(W) connectome/ER ≈ 49×).  
- Low statistical power (5 seeds × 20 trials) could miss ~0.15 effects.

**Portfolio framing:** highlight *debugging experimental validity* and *refusing to ship a fake null*, not the 0.76 number.

### Phase C — Instrument repaired (done, tested)

Committed fixes (see `reports/E1_audit_fixes.md`):

- Pass `input_ids` so probes exclude driven units; alive check requires **non-input spikes**.  
- Versioned results + provenance (UTC, git rev, harness/config hashes).  
- Spectral gain (`flylab/spectral.py`) + gain sweeps.  
- Real degree-preserving null (directed double-edge swap).  
- Positive-control gate PC-A / PC-B (activity + structure resolution).  
- Parameter-matched MLP (±10% of readout param budget) + ridge sweep.  
- 45 unit tests; git history from broken baseline commit upward.

**Positive controls (powered):** PC-A and PC-B **pass** at 12 seeds × 60 trials/class — the instrument can resolve activity and (with power) structure. Same gate **fails** under the old 5×20 protocol (power, not absence of effect).

### Phase D — First honest E1 topology comparison (done)

`null_ensemble` run: **12 seeds × 60 trials/class × 20 null draws**, rate-matched gains (not ρ-matched), commit `fe089d3`.

| Arm | Mean accuracy ± 95% CI |
|---|---|
| Connectome signed | **0.634 ± 0.122** |
| ER null | 0.651 ± 0.017 |
| Degree-preserving null | 0.685 ± 0.030 |
| MLP (matched ~995 params) | 0.642 ± 0.123 |

**Verdict (publishable negative):** connectome does **not** beat rate-matched nulls; CIs on differences include zero. Artifact:  
`experiments/results/e1_null_ensemble_powered_20260915T130422Z_fe089d3.json`

### Phase E — Glutamate polarity sensitivity (done)

Default policy left glutamate as UNKNOWN → ~60% of subgraph edges zeroed (ops proxy inflated ~2.5×). Sensitivity arms:

| Glu policy | Fraction zeroed | Acc ± CI (8 seeds) |
|---|---|---|
| unknown (reference) | 60.1% | 0.677 ± 0.137 |
| inhibitory (GluClα) | 46.7% | 0.677 ± 0.135 |
| excitatory | 46.7% | 0.627 ± 0.156 |

**Verdict:** Glu mapping changes sparsity/ops; **no significant accuracy shift** at this power. Artifact:  
`experiments/results/e1_polarity_arms_20260915T140857Z_fe089d3.json`

### Still open (good “next” bullets for portfolio)

- Wire PROTOCOL ablations (`|w|`, weight permutation, top-k hub removal) into the powered harness (library exists; full powered runs pending).  
- LSTM / GPU baselines when hardware allows.  
- Larger subgraphs / plasticity (O3+) only after E1 protocol stays gated.  
- Registry / `PROJECT_STATE` polish; keep Lightsail stopped when idle (credits).

---

## How to write this for a portfolio (instructions to Claude)

### Do claim

- End-to-end **scientific software** for connectomics → computation.  
- **Experimental hygiene:** leakage audits, positive controls, power analysis, versioned provenance.  
- **Honest negative result** under a powered, rate-matched null ensemble.  
- Sparse systems / spectral gain / signed E-I graphs on a full CNS-scale connectome slice.  
- Cloud ops on constrained CPU VPS without GPU.

### Do not claim

- “Fly brain beats AI” / Doom / lightsaber as evidence.  
- That early 0.76 scores were valid topology measurements.  
- That MaleCNS is a foundation model or neuromorphic AGI.  
- Exact published neuron/edge targets as if forced in code.

### Suggested CV bullets

1. Built a reproducible MaleCNS v1.0 → sparse signed graph pipeline (165k nodes / 25.6M edges) with checksum locks and Traced-filter validation.  
2. Designed an E1 reservoir harness with positive-control gates, spectral gain control, and degree-preserving nulls; fixed label leakage that invalidated early runs.  
3. Ran a powered connectome-vs-null study (12×60×20); reported a **negative** topology result with 95% CIs and matched MLP baselines.

### Suggested case-study title

**“When the nulls are honest: auditing a fly-connectome reservoir experiment end-to-end”**

### Keywords

`connectomics` · `sparse graphs` · `reservoir computing` · `LIF` · `experimental design` · `null models` · `scientific Python` · `AWS Lightsail` · `reproducibility`

---

## Paths Claude should cite

On the Lightsail machine (or synced copy of the repo):

- `reports/E1_audit_fixes.md` — full bug table and measurements  
- `experiments/PROTOCOL.md` — evidence rules  
- `experiments/results/e1_null_ensemble_powered_*.json` — powered E1  
- `experiments/results/e1_polarity_arms_*.json` — Glu sensitivity  
- `docs/PORTFOLIO_BRIEF_FOR_CLAUDE.md` — this file  
- `data/raw/` — **read-only**; never modify  

Primary data citation: Male CNS Connectome v1.0, Janelia (`https://male-cns.janelia.org/`), license CC-BY.

---

## Status snapshot

| Item | Status |
|---|---|
| Raw data verified | Done |
| Sparse graph + polarity | Done |
| Leak / null / gain audit | Done |
| PC gate (powered) | Pass |
| E1 connectome vs nulls (powered) | **Negative (honest)** |
| Glu polarity arms | Done (acc insensitive; sparsity changes) |
| Ablation suite powered runs | Pending |
| Work paused | Yes (user request 2026-09-15) |

