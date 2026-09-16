# EXP-MEM-002 Q0 — instrument result

Q0 completed with all 72 registered seed/delay checkpoints written under:

`experiments/results/EXP-MEM-002/q0_20260916T054112Z_d6a9572/q0/`

The aggregate gate is `INSTRUMENT_INCOMPLETE`. No delay had all five arms
`LIVE` and rate-matched in both independent train and test splits for all 12
seeds. The aggregate retained 263 arm/cell rows as `MISSING` (connectome 62,
DP 30, weight permutation 44, ER 55, ring 72). Calibration itself found a
common target within the 10% convention for only one of the 12 seeds; the
other seeds retain their selected gains and non-matching diagnostics.

This is an instrument result only. No accuracy, AUC, or memory curve was
computed, and no row was dropped because an arm was silent. The one permitted
follow-up is map 2, preregistered in `protocol_map2.md`, using top-50 local
nodes by positive outgoing-weight sum.
