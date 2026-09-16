# EXP-MEM-001 — post-INST memory cycle

**Status:** FROZEN before post-INST smoke / sizing pilot  
**Preregistered UTC:** 2026-09-16 02:51:07 UTC  
**Owner:** research engineer; no outcome-driven retuning  
**Historical artifact:** `pilot_superseded/pilot_20260916T011917Z_dcc995f.json` remains immutable and is not part of this cycle.

## Question and hypotheses

How does useful binary-cue recall change over silent delay at matched active-synapse compute and matched per-seed firing rate? Does MaleCNS recurrence differ from a degree-preserving null? Two-sided: connectome may exceed, tie, or underperform DP-null. No biological-brain claim.

## Frozen task

- Subgraph: 500 highest out-degree nodes by existing `H.select_nodes`; derived graph only. Snapshot check: 23,708 stored entries, 9,471 nonzero signed edges after removing explicit zeros. This gives equal active synapse-step budgets across structural arms.
- Input map: 50 nodes (10% input fraction, sourced from `e1_config.json` only), partitioned into two fixed, disjoint 25-node cue groups. Balanced label 0/1 activates its group for one onset step; external current is zero thereafter. Cue amplitude is derived from the LIF threshold equation. Same seed-specific input IDs and cue schedule across all arms; inputs excluded from 48 fixed non-input probes (48 matches the INST measurement resolution).
- Base LIF voltage/time constants come from the shared simulator config; **no E1 firing target, gain, or effect size is inherited**. IV: delays [10, 25, 50, 100, 250, 500] steps; read only final-step probe spikes.
- Train, validation, test and rate-calibration streams are disjoint and deterministic. Labels are balanced in each split. Ridge selection uses a train-only validation split; reserved test accuracy is read once after selection.

## Arms and controls

Structural arms: signed connectome; degree-preserving directed rewires (DP, primary; 2 independent draws per task seed); fixed-topology weight permutations (2 draws/seed); exact-active-edge ER (2 draws/seed; random sign/uniform-weight law is a declared confound); directed ring (2 draws/seed; excitatory weight law is a declared positive-control confound). Thus each 12-seed tranche has 24 independent draws per null/control type; null RNG streams are separate from task seeds. DP/weight-permutation preserve the active edge count; ER/ring use the same 9,471 active-edge budget.

Controls: no-network constant/chance baseline (not subject to spike-liveness gate) and FIFO delay-line positive control (software/task plumbing only; not neural evidence). Torch is absent on this host. Use a real CPU tanh Elman RNN with 8 hidden units and full BPTT; its 98 trainable parameters (2×8 input + 8×8 recurrent + 8×2 output + 2 output bias) exactly match the 48-feature binary linear readout (48×2 + 2). It is not an LSTM/GRU; report this model mismatch and measured runtime.

## Rate and compute control

For each task seed and structural graph draw, calibrate on separate balanced cues at delay 100, 10 trials/class. Try 64 log-spaced normalized gains from 0.125 to 64; these bounds/grid are **# UNCALIBRATED GUESS**, used only for calibration, never selected by accuracy. For each seed, choose the lowest rate shared by live structural variants; choose each variant's gain minimizing relative rate error. Rate-match tolerance is ±10% (**# UNCALIBRATED GUESS**). Lock one gain per seed/graph draw across all six delays. If connectome/DP cannot be matched within tolerance, report the mismatch and do not claim a rate-controlled topology contrast. Report realized rate at every delay. Explicit-zero weights are removed before simulation and excluded from ops. Record active nnz × actual neuron-steps, wall time and CPU time per cell.

## Frozen sizing and run plan

1. Smoke: one task seed, connectome + one DP draw, delays 10 and 100, 4 trials/class/split. Check controls, cue routing, liveness and timing only; not evidence and not included in sizing.
2. Sizing pilot: seeds 100–105, 30 trials/class in train and test, all six delays and structural arms. Pilot seeds are separate from confirmation and contribute only to the preregistered power calculation; never to claims or hyperparameter selection.
3. Confirmation tranche 1: seeds 0–11, 100 trials/class in train and test. If inconclusive under the rule below, one and only one extension uses seeds 12–23 with the same protocol. No seed/delay tuning.
4. Pilot-based planning: let (s_d) be the sample SD across six sizing-seed paired differences in normalized trapezoidal AUC (connectome minus mean of two DP draws). The target difference δ=0.05 accuracy-AUC units is **# UNCALIBRATED GUESS**; 80% power and two-sided 95% confidence are planning conventions. Compute (N=ceil(((z_{.975}+z_{.80})s_d/δ)^2)); planned total is 12 if (N\le12), otherwise 24 (one extension only). If (N>24), report the design as underpowered at the registered compute cap; do not change δ or the task.

## Metrics, gate, and decision

- Per arm × graph draw × seed × delay: test accuracy, train/test liveness separately, non-input and probe spike rates, calibrated gain/rate, active nnz, effective synapse-step ops, wall/CPU time, and provenance hashes. Keep every failed row. `check_alive` requires non-input spikes, non-degenerate features (≥2 unique rows; binary-task minimum), and finite stats on **both** train and test. Any required silent/dead split invalidates that seed/contrast; never drop it from the mean.
- Primary curve: accuracy by delay with across-seed 95% t intervals. Primary contrast: paired normalized trapezoidal AUC over the registered delay range, connectome minus per-seed mean DP accuracy. Per-delay contrasts and other arms are secondary/descriptive; no test-based model or gain selection.
- FIFO must return 1.0 and the balanced no-network baseline 0.5. All required network arms must pass split liveness; primary connectome-vs-DP rate error must be ≤10% on calibration. Failure is INVALIDATED for the affected contrast, not a Fly loss.
- Classify AUC result: CI wholly above +δ = higher; wholly below −δ = lower; wholly within [−δ,+δ] = approximate tie; otherwise INCONCLUSIVE. If tranche 1 is inconclusive, run the single 12-seed extension. No indefinite expansion.
- If activity/leakage invalidates the measurement, repair **only the input mapping**, run once under a versioned protocol amendment, and if still dead set `status: HUMAN_STOP`. If a valid interpretable curve results, Q2 is EXP-A-001 on this same task (parameters/FLOPs/latency; state mismatches). Q3 EXP-GLU-001 follows MEM only if the protocol is live.

## Cost and integrity

Measured design inputs: 9,471 active edges at N=500, 2 vCPU / 15 GiB, no GPU; torch unavailable. Initial smoke+sizing+12-seed tranche entails 67,692,240 registered LIF step calls plus RNN/null-generation work. Engineering-only pilot telemetry at N=128 was 0.0615 s / 1,920 LIF steps; extrapolating by active edges and registered call count gives a rough **2–3 h** for initial work and leaves the single 12-seed extension under the ~4 h box budget. This is a cost estimate, not a scientific result; runtime uncertainty is high. Approximate peak drive-array memory is <1 GiB in addition to the loaded graph; verify before full run. If smoke-based projection exceeds 4 h, freeze a reduced delay grid in a dated protocol amendment **before** confirmatory metrics; never silently reduce seeds/trials.

All outputs go under a unique `post_inst_<UTC>_<gitrev>/` run directory; write calibration and each seed/delay cell atomically as it finishes. Save protocol/code/config/graph SHA-256 in every artifact. Refuse overwrite; preserve checkpoints on interruption. Never read/write `data/raw/` or rebuild `data/derived/graph/`.
