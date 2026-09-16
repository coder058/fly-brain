# EXP-IGNITE-001 — primary pair ignition map

**Status: FROZEN before metrics.** This is an operating-point instrument
experiment. It is not a classifier, not a memory result, and not a claim that
the connectome wins.

## Question

For which seed and independently chosen connectome/DP gains do both primary
arms pass train/test liveness and fall inside the same firing-rate band?

## Frozen design

- Dataset: the existing MaleCNS v1.0 selected `n=500` subgraph. `data/raw/`
  and the committed `data/derived/graph/` artifacts are read-only; no graph
  rebuild is allowed.
- Primary arms: signed connectome (`connectome_signed`) and one
  degree-preserving draw per task seed (`degree_preserving`). The DP RNG stream
  is derived from the protocol hash, seed, arm name, and draw index and is
  recorded in every checkpoint.
- Secondary arms are optional only (`weight_perm`, `er`, `ring`). A missing
  secondary never invalidates a primary pair and no secondary arm gates the
  result.
- Input map: deterministic protocol-hash-ranked local nodes, first 50, split
  25/25 between cue 0 and cue 1. This is deliberately not top-positive-
  outdegree and not positive-weight-sum, and is not selected by activity.
- Probe map: the existing deterministic non-input probe selector, 48 probes.
  Probes may not overlap the 50 inputs.
- Stimulus: existing binary cue generator, cue only at step 0 and zero
  external input afterwards; train and test are generated independently. The
  ignition instrument records no accuracy, AUC, classifier, or readout.
- Trials: 10 per class per split for full/sizing cells; smoke uses 2 per class.
- Gain grid: 16 logarithmically spaced values from `0.05` to `80.0`, inclusive.
  This covers the range used by the existing E1 gain matcher. `80.0` is the
  hard cap; no gain search outside this grid is allowed.
- Rate target and band: target non-input firing rate `0.002`; train and test
  rates for each arm must both be within a preregistered relative band of
  `20%` of that target. This wider band is an explicit new ignition
  instrument convention because the prior 10% MEM band produced no usable
  pair; it is not a biological threshold and cannot be tightened or widened
  after inspecting results.
- Liveness: run `check_alive` independently on train and test for every
  arm/seed/gain. A primary arm candidate is live only when both splits pass and
  both realised rates are in-band. Retain every failed candidate as `MISSING`
  with its reason.
- Stages: smoke is seed 0; sizing is seeds 0, 1, 2. If sizing finds at least
  one primary pair, run the 12-seed confirmatory candidate cells using the
  frozen grid and same protocol. If sizing finds no pair, run the same frozen
  grid for all 12 seeds once to distinguish a sizing miss from no co-ignition.
  A full run is never silently reduced because of runtime; if projection
  exceeds roughly four hours, record the pre-metric recut and stop before
  metrics.

## Pair output and gate

Each pair cell is `(seed, connectome_gain, dp_gain)`. `pair_alive` is true only
when both primary candidates are live and rate-matched on train and test. The
output is the list/table of pair cells, gains, realised rates, liveness, and
compute; accuracy is always absent. Secondary missingness is reported but does
not remove a primary pair.

If no pair exists under the cap, close this ID as `NO_COIGNITE`: this is a fact
about the tested instrument protocol, not “Fly lost,” not “the connectome has
no memory,” and not “biology has no value.” If at least three pair cells exist,
the next scientific ID is EXP-MEM-004 using only the co-ignited gains. Do not
run MEM-004 from a single exploratory cell.

## Safety and provenance

Use a new append-only directory `ignite_<UTC>_<git>/` below this experiment.
Write one immutable checkpoint per seed/gain/arm and never overwrite prior
MEM, GLU, INST, graph, or raw artifacts. Each JSON records protocol/runner/
config/graph hashes, map rule, DP seed, gain, target/band, rates, liveness,
pair status, and resource timing. Stop only for human `STOP`, protected-data
access, graph overwrite, INST conclusion overwrite, disk/RAM/cost risk, or a
dead process requiring recovery.
