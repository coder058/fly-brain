# FLY LAB — Experiment protocol (evidence first)

**Owner:** jobi  
**Machine of record:** Ubuntu-1 (`/home/ubuntu/fly-lab`).  
**Gate:** no runs until MaleCNS **v1.0** raw feathers pass SHA-256. Dataset is frozen — do not re-download.

## Principle
Visual demos ≠ evidence. Evidence = reproducible metric vs **strong baseline** + ablation + efficiency proxy, **after** the PC-A/PC-B gate, at adequate power.

## E0 — Validation (blocking)
- [x] `connectome-weights-…minconf-0.5.feather` SHA-256 = `e35da783…afc1`
- [x] annotations SHA-256 = `2177e246…a3b2`
- [x] neurotransmitters SHA-256 = `95c92892…9621`
- [x] Computed `|V|`, `|E|` from files. **Actual:** 165,122 neurons / 25,563,197 directed edges / Σw = 124,025,046. Published targets (~166,700 / ~25,582,938) differ by 0.95% / 0.077% — documented, **not** forced. Filter: `status==Traced` both ends. Never touch `data/raw/`.

## Hard rules (audit 2026-09-15)
- Never claim the pre-fix “0.76 ≈ ER/shuffle” as a topology result. It was **label leak + dead non-input reservoir**.
- `input_ids` must reach `simulate_driven`. `check_alive()` requires **non-input spikes**, not just feature variance.
- Compare arms at **matched non-input firing rate**, not matched ρ. ρ(connectome)/ρ(ER) ≈ 49× on the 500-node subgraph; equal ρ ≠ equal activity.
- Subgraph is **inhibition-dominated** (signed λ_max ≈ −2131). ρ=1 is not excitatory ignition. Operating gain is ~5–12, not 0.71.
- **Power:** E1's registered measurement used **12 seeds × 60 trials/class**. That sample size and its gates do not automatically transfer to other tasks.
- PC-A / PC-B are E1 controls. Each new task needs controls that validate its own measurement; a ring is not required to beat ER for memory instrumentation to be valid.
- Results are versioned (`<prefix>_<UTC>_<git rev>.json`). **Never overwrite.**
- Null ensemble RNG stream is independent of task seeds. ≥20 draws per null type.
- Glutamate is a **named sensitivity arm**, never a silent UNKNOWN→0 default for the only reported number.
- MLP / LSTM within **±10%** of readout parameter budget. Ridge is a **sweep**, not `ridge=10`.
- `ops_proxy` must not count explicit-zero (UNKNOWN) edges as synaptic ops.

## E1 — Minimal computational evidence
**Task:** fixed-connectome reservoir + linear readout on held-out temporal classification.

**Connectome arm:** sparse signed weights (E / I / UNKNOWN). UNKNOWN not forced excitatory. Report glutamate_unknown / glutamate_inhibitory / glutamate_excitatory.

**Nulls (required):**
1. Erdős–Rényi same `|V|,|E|` (no self-loops)
2. Degree-preserving directed double-edge swap (`flylab.nulls.degree_preserving_null`) — **not** dest-permutation
3. Weight permutation on **fixed topology**

**Ablations:**
- drop E/I signs → `|w|` (`connectome_abs`)
- weight permutation (topology fixed)
- remove top-k hubs (incident edges dropped)

**Strong baselines (same trainable param budget as readout ±10%):**
- MLP (width chosen to land in budget)
- LSTM/GRU still deferred (no GPU); do not fake it with an over-parameterised MLP

**Metrics:** accuracy (primary) + 95% CI; ops per synapse-step (nonzero nnz only); signed vs `|w|`.

**Pass criterion (E1):** PC-A/PC-B pass **and** connectome beats **both** ER and degree-preserving nulls on primary metric (n≥12 seeds, mean±95% CI, null ensemble ≥20 draws) **and** matches or beats budget-matched MLP at ≤1× ops, **or** beats it at ≤0.5× ops. Visual Doom never counts.

If the connectome **ties** its nulls at this power, that is a **real negative** — write it as such. Do not re-run weaker protocols to fish a win.

## E2+ (later)
Plasticity (O3), shift (O5–O6), evolution (O8) remain later tracks. EXP-MEM-001 can run its own task-specific pilot; its confirmatory run requires a separately frozen protocol and valid memory controls, not an automatic pass from EXP-INST-001.

## EXP-MEM-001 — preregistration contract

**Question:** how does recall accuracy change with delay after one binary cue, and how does that curve compare with a degree-preserving topology control and small conventional recurrent baselines?

- At trial step 0, deliver one balanced binary cue to a fixed input set. External input is exactly zero for every later step. Labels are not features and are never delivered again.
- Probe only non-input neurons. The primary readout uses only the final-step activity at the requested lag; no earlier bins, input IDs, trial IDs, or lag-derived labels enter the classifier.
- Generate independent balanced train and test trials from disjoint deterministic random streams. Select readout regularization using training-only validation; inspect the reserved test set once after the protocol is frozen.
- Report every seed/arm/lag, including dead or degenerate features. Keep failed rows in raw artifacts; any failed required seed makes the confirmatory contrast invalid rather than silently dropping it.
- Validate task plumbing with a FIFO delay line of known capacity (positive control) and a memoryless/no-network control. The FIFO is a software control, not evidence about neural memory. A ring-vs-ER difference is descriptive and is **not** required for instrument validity.
- Confirmatory structural arms: connectome, degree-preserving null (primary topology control), fixed-topology weight permutation, ring and ER (with ER's degree/weight confounds reported). Report per-arm non-input firing rate, activity validity, lag curve, and paired uncertainty.
- Compare CPU-tiny LSTM, GRU, Transformer and sparse-RNN baselines only at matched parameter budgets, with measured wall/CPU time. Torch is absent on the machine at audit time; first measure installation/runtime feasibility. Do not replace unavailable models with an over-sized MLP or describe them as run.
- Pilot results are exploratory only. Freeze the lag grid, operating/rate-matching rule, graph size, probes, sample count/power target, baselines and analysis before confirmation. No E1 seed count, effect threshold, firing target, or gain transfers by default. Choose sample size from pilot variance only; never tune on reserved confirmation data.
- Record all pilot, failed, restarted and confirmatory attempts with code/data hashes. The experiment remains `not claim-ready` until the frozen run and controls pass.

The current `memory_task.py` delay-line test exercises task/evaluator plumbing only. It is not a neural delay circuit, a topology result, or a frozen protocol.

### Pilot disposition — 2026-09-16

The pre-INST exploratory pilot at `experiments/results/EXP-MEM-001/pilot_superseded/pilot_20260916T011917Z_dcc995f.json` is **SUPERSEDED/INVALIDATED**; it is not confirmed and is not cited as a memory result.

## Artifacts
```
experiments/
  PROTOCOL.md
  harness/
  results/          # versioned JSON only; never clobber
  registry.json     # experiment index
```
