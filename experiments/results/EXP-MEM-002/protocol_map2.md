# EXP-MEM-002 map-2 follow-up — instrument viability

**Status: FROZEN before execution.** This is the one permitted second input
map after Q0 found no complete delay. It is still an accuracy-blind instrument
check; it is not a rescue search and is not a topology result.

All design choices, delays, seeds, arms, trials, gain cap, calibration target
selection, liveness guard, rate tolerance, append-only checkpointing, and gate
are inherited unchanged from `protocol.md`. The only registered change is the
input map:

- Load the same existing `n=500` induced graph; never touch `data/raw/` or
  rebuild `data/derived/graph/`.
- Score each local node by the sum of its positive active outgoing edge
  weights, ties by local index, select the top 50, alternate selected nodes
  into cue 0 and cue 1, and derive probes deterministically while excluding
  inputs.
- The rule is frozen before looking at map-2 outcomes. It uses no accuracy or
  delay performance for selection.

The Q0 gate remains `INSTRUMENT_COMPLETE` only if every one of the five arms is
`LIVE` in independent train and test splits at every registered delay for all
12 seeds. A cell failing either liveness or rate-match is `MISSING` and remains
visible. No accuracy, AUC, or memory curve is computed by this map check.

If map 2 also has no complete delay, the memory queue does not branch to
EXP-A/EXP-GLU; the next action is the preregistered E1 hygiene alignment.
