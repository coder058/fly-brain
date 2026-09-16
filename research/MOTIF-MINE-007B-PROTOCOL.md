# MOTIF-MINE-007B — global degree+reciprocity null

## Status

This protocol is frozen before MOTIF-MINE-007B metrics. It is a structural
control, not a behavior, memory, biology, novelty, or ML-transfer claim.

## Question

Does the corrected non-induced FFL enrichment survive a null preserving exact
directed in/out degrees and reciprocal-pair count, while allowing global
endpoint mixing and intentionally not preserving superclass blocks?

## Frozen graph

Use the same read-only MaleCNS v1.0 graph and exact 500-node top-out-degree
subgraph as MOTIF-MINE-005: unsigned edge presence, UNKNOWN topology edges
retained, 4 source self-loops removed, and 23,704 analyzed edges.

## Null construction

Decompose edges into singleton directed units and reciprocal two-edge units.
For singleton units, use global directed two-edge swaps. For reciprocal units,
use global endpoint swaps that replace two reciprocal pairs with two reciprocal
pairs. Each accepted swap preserves exact node in/out degree and reciprocal
pair count. Reject loops, duplicates, collisions, and no-op swaps. Blocks are
intentionally not preserved and are reported as a secondary diagnostic.

Use 20 accepted swaps per unit, seeds 0..19, and a bounded attempt cap of
10 times the target per unit family. If the cap is reached, the null is
incomplete and not scored as a negative. Report accepted/target swaps,
attempts, mixing, all invariants, and all null draws.

## Measurements

Primary: non-induced directed FFL occurrences. Secondary: corrected induced
FFLs and induced directed 3-cycles. Report observed, null mean, sample SD,
delta, and all draws. Smoke is one seed and is not evidence. No p-value gate
is preregistered.

If non-induced enrichment remains, degree plus reciprocity did not explain it;
block/spatial structure and unit selection remain alternatives. If it
collapses, record only the narrow reciprocal-closure interpretation. No
biological or ML claim is licensed.

## Reproducibility

Estimate CPU/RAM before full. Run one process only. Write immutable protocol,
runner, hashes, smoke, sizing, null checkpoints, and summary under
research/results/MOTIF-MINE-007B/FULL_<timestamp>_<gitsha>. Never overwrite
earlier artifacts or touch raw/protected graph data.
