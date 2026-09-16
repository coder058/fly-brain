# EXP-MEM-002 map 2 — instrument result

Map 2 completed with all 72 registered seed/delay checkpoints written under:

`experiments/results/EXP-MEM-002/q0_20260916T055512Z_cd028e2/q0/`

The aggregate gate remains `INSTRUMENT_INCOMPLETE`. No delay had all five arms
`LIVE` and rate-matched in both independent splits for all 12 seeds. The
aggregate retained 277 arm/cell rows as `MISSING` (connectome 62, DP 38,
weight permutation 52, ER 56, ring 69). No accuracy, AUC, or memory curve was
computed.

This was the one registered second map, using top-50 local nodes by positive
outgoing-weight sum. The instrument queue therefore does not open EXP-A or
EXP-GLU. E1 hygiene is complete in commit `dfdf7dd`; the full test suite is
`72 passed`.
