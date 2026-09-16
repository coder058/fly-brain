# EXP-MEM-001 mapping repair — 2026-09-16

## Disposition

`INVALIDATED` after the one preregistered accuracy-blind input-map repair; the scientific loop is now `HUMAN_STOP`.

Artifact: `experiments/results/EXP-MEM-001/post_inst_mapping_repair_20260916T031717Z_dcc995f/sizing/summary.json`

The repair replaced random-per-seed input selection with the frozen static rule: top 50 local nodes by positive active outgoing-edge count in the top-500 signed induced graph, ties by local index, alternated into two cue groups. It changed no other task, graph, delay, rate, readout or analysis parameter.

All six calibration seeds passed the primary connectome/DP rate-match check. Required network liveness still failed in five cells: `ring-1` at seed 100/delay 10, `dp-1` at seed 101/delays 250 and 500, and `weight_perm-1` at seed 102/delays 50 and 250. The primary connectome-minus-DP AUC had zero complete paired seeds, so no memory curve or topology comparison is interpretable. These failures are instrumentation invalidation, not a negative result for the connectome.

Per the frozen amendment, no second map or operating-point attempt is made. `EXP-A-001` and `EXP-GLU-001` are not run.
