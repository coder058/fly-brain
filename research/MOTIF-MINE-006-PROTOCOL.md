# MOTIF-MINE-006 — reciprocity-preserving closure control

## Status

This protocol is frozen before MOTIF-MINE-006 metrics. It is a structural
control, not a behavior, memory, biology, novelty, or ML-transfer claim.

## Question

Does the corrected non-induced feed-forward-loop enrichment survive a null that
preserves directed in/out degree, superclass source-to-destination blocks, and
the number of reciprocal edge pairs?

## Frozen graph

Use the same read-only MaleCNS v1.0 graph and exact 500-node top-out-degree
subgraph as MOTIF-MINE-005. Build unsigned edge presence from all graph edge
coordinates, retain UNKNOWN zero-weight edges as topology, remove self-loops
explicitly, and record the resulting 23,704-edge graph. No raw or protected
derived graph may be written.

## Null construction

Generate 20 reciprocity-preserving nulls with seeds 0..19. Split the graph into
single directed-edge units and reciprocal two-edge units. Apply directed
two-edge swaps within identical source/destination superclass blocks for
single units. Apply reciprocal-pair endpoint swaps within identical ordered
superclass-pair classes for reciprocal units. Each accepted swap preserves node
in/out degree; the construction must also preserve edge count, exact block
counts, zero self-loops, no duplicates, and reciprocal-pair count.

Use 20 accepted swaps per unit, with a bounded attempt cap recorded per group.
Do not pool this null family with earlier degree/block nulls. Missing or failed
invariants are a run failure, not a negative.

## Measurements

Primary: non-induced directed feed-forward occurrences. Secondary: corrected
induced feed-forward triads and induced directed 3-cycles, counted once per
cycle with explicit integer adjacency. Report observed count, null mean, sample
SD, delta, all draws, and structural invariants. No p-value gate is
preregistered.

## Interpretation gate

If non-induced enrichment remains, it is not yet a computational primitive:
reciprocity is only one confound and spatial/neuropil structure, unit selection,
and annotation remain. If it collapses, record that reciprocal closure explains
the tested non-induced signal under this null. Neither outcome supports a
biological or ML claim without a functional experiment.

## Compute and reproducibility

Smoke is one seed per family and is not evidence. Estimate CPU/RAM before full.
Run one process only. Write immutable protocol, runner, hashes, smoke, sizing,
all null checkpoints, and summary under
research/results/MOTIF-MINE-006/FULL_<timestamp>_<gitsha>. Never overwrite
earlier artifacts or touch raw/protected graph data.
