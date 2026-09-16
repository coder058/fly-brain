# EXP-MEM-002 — memory instrument viability

**Status: FROZEN before execution.** This is an instrument experiment, not a
memory-accuracy curve and not a topology result.

## Question

Can the connectome and four registered structural controls remain alive in
both independent train and test splits at every registered delay, with a
gain chosen separately for each arm and seed, while staying rate-matched under
a preregistered gain cap?

If an arm does not meet the liveness or rate gate in a cell, that cell is
`MISSING`. It is not a loss for that arm and it is not silently removed.

## Frozen design

- Dataset: the existing MaleCNS v1.0 derived graph and the existing selected
  `n=500` induced subgraph. `data/raw/` and the original
  `data/derived/graph/` files are read-only for this experiment.
- Arms: `connectome`, degree-preserving (`dp`), fixed-topology weight
  permutation (`weight_perm`), Erdős–Rényi (`er`), and ring (`ring`). One draw
  per control family per seed is used for this instrument check.
- Graph construction: the existing `create_graph_variants` implementation;
  explicit zero entries are excluded from the active edge budget. No graph
  rebuild is permitted.
- Input map: the previously registered accuracy-blind repair map: rank local
  nodes by positive active outgoing-edge count, ties by local index, take the
  top 50, alternate them between cue 0 and cue 1, and use a deterministic
  non-input probe map. This map is fixed before Q0 and is not selected by
  performance.
- Delays: `10, 25, 50, 100, 250, 500` simulation steps. The cue is present only
  at step 0; all later external-current values are zero.
- Seeds: `0..11` (12 seeds). Every seed writes its calibration and cell JSON
  incrementally.
- Trials: 10 per class per split for Q0 (`train` and `test` generated
  independently). Smoke uses 1 seed, delays 10 and 100, and 2 trials per
  class; smoke is a runtime/serialization check and is not evidence.
- Calibration: at reference delay 100, 10 trials per class, per arm and seed;
  candidate gains are `64` logarithmically spaced values from `0.125` through
  `64.0`. These bounds and resolution are preregistered calibration choices,
  not fitted findings. The selected gain is locked across all delays for that
  arm and seed.
- Rate matching: at calibration, retain live positive-rate candidates for all
  five arms. Select the candidate target that minimizes the worst relative
  error across arms (ties: mean relative error, then lower target), then select
  each arm's nearest live candidate. A candidate is rate-matched only when its
  relative error is at most 10%. The 10% tolerance is an uncalibrated
  instrument convention, not a biological threshold.
- Liveness: call `check_alive` separately on train and test features. A cell is
  `LIVE` only if both splits pass liveness and both realised rates are within
  the selected calibration target tolerance. Otherwise it is `MISSING`, with
  the failed split/rate reason retained.
- Readout: no accuracy, AUC, classifier, or curve is computed in Q0. Q0 only
  tests whether the measurement instrument supplies complete, rate-matched
  cells.

## Gate and follow-up

`INSTRUMENT_COMPLETE` requires every arm to be `LIVE` for all 12 seeds at all
six delays. A delay is eligible for a later Q1 curve only when every required
arm and seed at that delay is `LIVE`. `INSTRUMENT_INCOMPLETE` is a valid Q0
outcome and does not say that the connectome lost.

If no delay is complete, one second deterministic input map may be registered
and tested. If that also yields no complete delay, do hygiene work on the E1
runners and stop the memory science queue; do not run EXP-A or EXP-GLU on an
incomplete instrument.

## Provenance and safety

Every JSON records the protocol hash, runner hash, graph hashes, config hash,
git revision, map rule, gain cap, calibration candidates, liveness reports,
and all missing cells. JSON is append-only: reruns resume only from matching
checkpoints in a new `q0_*` root and refuse provenance mismatches. A smoke
runtime is measured before the full job; if its extrapolation exceeds roughly
four hours on this box, the run is stopped and reported rather than silently
reducing the registered design.
