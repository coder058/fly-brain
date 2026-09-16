# EXP-MEM-001 — mapping-repair amendment

**Status:** FROZEN before the single mapping-repair re-run  
**Base protocol:** `experiments/results/EXP-MEM-001/protocol.md`  
**Base protocol SHA-256:** `5b13c9af4540b4441045c6069145ca404513b808031e071f92f7b8a4bc981bd4`  
**Purpose:** repair the input map after the base sizing was `INVALIDATED` by liveness/rate calibration failures.

The base question, binary cue task, six delays `[10, 25, 50, 100, 250, 500]`, top-500 graph, 48 non-input probes, train-only readout selection, structural arms, calibration grid, liveness guard, rate-match tolerance, metrics, gate, and failure interpretation remain unchanged. This amendment changes **only the input mapping**.

## Mapping repair (frozen, accuracy-blind)

For the existing top-500 induced signed graph, score each local node by the count of positive, nonzero outgoing edges to the induced 500-node subgraph. Select the 50 highest-scoring nodes; ties are resolved by lower local node index. Keep this selected set fixed for every task seed and every graph arm. Alternate the ranked selected nodes between cue group 0 and cue group 1 (25 nodes each). Exclude the union from the 48 fixed probes. No score, label, test accuracy, or firing metric is used to select the map.

This is a static routing repair only: it does not change graph weights, polarity, delay, gain grid, trial counts, readout, or analysis. The previous random-per-seed maps and their invalidated artifacts remain preserved and are not reused.

## One re-run

Run exactly one fresh sizing tranche using seeds `100–105`, 30 train and 30 test trials per class, all six delays, two DP/weight-permutation/ER/ring draws per seed, the registered calibration at delay 100, and the software FIFO/no-network controls. Write to a new `post_inst_mapping_repair_<UTC>_<gitrev>/` directory with atomic per-seed/per-delay checkpoints. This tranche is not evidence unless its frozen liveness/rate gates pass; it is the sole test of whether the mapping repair rescues the instrument.

If any required map-repair tranche remains invalidated by dead splits or failed primary rate matching, classify MEM as `HUMAN_STOP` for this loop; do not alter another constant or try another map. If it yields a live interpretable curve, proceed to the registered Q2 branch: `EXP-A-001` on the same memory task. No Q3 sensitivity is run before that decision.

**Integrity:** do not touch `data/raw/`, do not rebuild `data/derived/graph/`, do not overwrite any prior artifact, and preserve all failed rows/checkpoints.
