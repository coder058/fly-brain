# EXP-E2-HD — Does the head-direction circuit's map carry position better than rewirings?

Status: **preregistered**. Committed and pushed before any confirmatory seed is run.

## Why a new question

The E1 lineage ([closed](../../../reports/EXP_E1_MATCH.md)) asked whether a *degree-ranked*
500-neuron slice computes better than rewirings, and found no support. A slice chosen by
connection count has no reason to implement any particular computation. This experiment asks
the same kind of question of a circuit with a known function: the fly's head-direction
system, where EPG neurons tile the protocerebral bridge (PB) by heading, PEN neurons shift
the representation and Delta7 neurons provide ring-wide inhibition. If the instrument can
see wiring effects anywhere, it should see them here; if it cannot, that bounds what the E1
negative means.

## Circuit

`data/e1_slice/hd_circuit.npz` (tested in `tests/test_hd_circuit.py`): all 152 traced EPG,
EPGt, PEN_a, PEN_b, PEG and Delta7 neurons of MaleCNS v1.0; 9,160 connections; signs from
each presynaptic neuron's transmitter with glutamate inhibitory (Delta7 → −1; under the E1
default policy Delta7 output would be zero). PB glomerulus labels from instance names.

## Task

Eight classes: a 5-step current pulse (amplitude 4.0) into the EPG neurons of one right-PB
glomerulus R1…R8 (2–4 neurons each). All neurons receive Gaussian noise (σ = 0.6) every
step. Features: mean spikes of the 129 **pool** neurons — every neuron except the 23
right-side EPGs that can ever receive a pulse — over a 5-step window ending 5, 15, 30 or 60
steps after the pulse. Ridge readout, 40 trials per class, 70/30 within-class split. Chance
is 0.125. LIF: τ_m = 6, threshold 1, reset 0 (as E1).

## Arms

| arm | what it keeps | what it destroys |
|---|---|---|
| `connectome` | everything | — |
| `dale_degree_null` (10 draws) | in/out degree, each neuron's outgoing weights and sign | who connects to whom |
| `topography_null` (10 draws) | the above **and** every cell-type→cell-type edge count | which neuron *within* a type connects to which — the map |
| `no_network` | — | all recurrent connections (calibration) |

## Fairness: equal tuning budget

An **exploratory pilot on dev seeds 0–1** (not part of this test) found the circuit bistable
under this model: below a critical gain the pool falls silent after the pulse, above it the
pool fires at ≈0.2–0.8 spikes/neuron/step. Matching firing rate, as E1 did, would place every
arm on that cliff. Instead every graph is simulated on the same 12-value gain grid
{1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 8, 12, 16} (gain = spectral-radius-normalised coupling) and,
**per delay, the gain with the best validation accuracy on training trials only** is tested
once. Gains at which the training features are degenerate (< 10 distinct rows) are not
candidates; an arm with no candidate scores "no measurement" (expected for `no_network`).

The pilot also showed (dev seeds 0–1, 2 null draws): delay 5 — connectome 0.99, nulls
0.76–0.79; delays ≥ 15 — all arms 0.16–0.27. That shaped the endpoint choice below.

## Seeds

**6000–6023 (24 seeds)**, never used. Null draws use RNG streams (70000, d) and (70001, d).

## Endpoints

Paired by seed (null value = mean over its draws), mean and two-sided 95% t-interval.

**Primary — delay 5: connectome − topography_null.**
Lower bound > 0 → "the head-direction map carries position better than the same circuit with
its map shuffled"; upper bound < 0 → worse; otherwise no detectable difference.

**Key secondary — delay 5: connectome − dale_degree_null.**

**Memory secondaries — delays 15, 30, 60, both comparisons.** Pilot accuracies were near
chance; these test whether the map adds *persistent* memory. No direction predicted.

Calibration: `no_network` must score no measurement or ≤ chance + 0.05 at every delay;
otherwise the run is reported as `TASK_LEAK` and no endpoint is claimed.

## What it can and cannot show

A positive primary means the map's convergence — same-position EPGs projecting onto shared
targets — carries a spatial signal one to two synapses downstream better than the same cell
types wired at random. It is a transmission result, not a ring-attractor memory result, and
it is expected from the anatomy; its value here is as a **sensitivity check of the
instrument** that returned "not supported" in E1. A null primary would mean the instrument
cannot see even an anatomically obvious wiring effect, which would weaken every E1 conclusion.

```
python experiments/harness/hd_memory.py --seeds 6000:6024 --label confirmatory
```
