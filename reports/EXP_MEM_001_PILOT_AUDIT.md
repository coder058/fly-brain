# Historical EXP-MEM-001 exploratory-pilot audit — 2026-09-16

## Decision

**Historical disposition: SUPERSEDED/INVALIDATED pre-INST exploratory pilot.** Not evidence for or against connectome memory; do not confirm or cite as a memory result.

Artifact: `experiments/results/EXP-MEM-001/pilot_superseded/pilot_20260916T011917Z_dcc995f.json`
SHA-256: `e866100d9e304088e6427e8290ec416ef08a8e36c0490c94f1355f5d48f06480`

## What the run actually established

- Task plumbing was correct in this pilot: one balanced cue at onset, zero later external input, independent train/test generation, and final-step probes excluded the input IDs.
- The software FIFO positive control scored 1.00; the memoryless control scored 0.50 on balanced test labels.
- At lags 1, 4 and 16, non-input spikes were exactly zero, feature standard deviation was zero, and scoring was correctly skipped. No connectome accuracy was measured.
- Each row used 40 train and 40 test trials, `n=128`, 13 randomly chosen input neurons, 48 probes, seed 0 and exploratory gain 12. These are pilot settings, not a frozen protocol.
- Measured total CPU time across the three lag rows was approximately 0.061 s; this only describes this tiny invalid pilot and does not estimate confirmation cost.

## Mechanistic diagnostic (static, not a new performance run)

Reconstructed the exact pilot subgraph and input selection. The 13 inputs had 275 directed edges into the non-input pool (106 distinct recipients), including 117 edges into 45 probes. Under the signed matrix, the maximum *aggregate signed incoming-weight sum* to any non-input neuron, assuming all 13 inputs spike together, was 0; the maximum absolute-weight sum was 2,443. This is consistent with the observed lack of excitatory propagation at this mapping/operating point, but does not prove the sole cause: the pilot's actual stochastic input-spike subsets and downstream trajectories were not separately audited. Do not convert this diagnostic into a biological claim.

## Current status

This immutable invalid pilot is historical only; the post-INST cycle is separately pre-registered at `experiments/results/EXP-MEM-001/protocol.md`. Keep E1 and EXP-006 closed and E1B disabled.
