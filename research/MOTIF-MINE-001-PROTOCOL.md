# MOTIF-MINE-001 — directed three-node motif inventory

## Status

This protocol is frozen before MOTIF-MINE-001 metrics. It is a structural
mechanism screen, not a behavior, memory, biology, novelty, or ML-transfer
claim.

## Question and hypothesis

Question: are directed three-node feed-forward loops and directed 3-cycles
enriched in the fixed high-out-degree subgraph relative to a degree-preserving
rewire?

The hypothesis is two-sided for each motif. Enrichment, depletion, or no
difference are all valid outcomes. A result cannot identify biological
function or establish a reusable ML primitive.

## Frozen graph and null

Use the existing read-only MaleCNS v1.0 graph and the exact 500-node
top-out-degree induced subgraph used by CIRCUIT-MINE and ROUTING. Use the binary
directed adjacency for motif presence; parallel edges and self-loops are not
counted. The observed graph and every null have the same node set, edge count,
in-degree, out-degree, and simple-edge constraint.

Generate exactly 20 degree-preserving nulls with the existing null constructor
and 20 accepted swaps per source edge, using independent null RNG streams.
No label, motif, or result is used to select the subgraph or null settings.

## Primary measurements

For the observed graph and each null, count:

1. directed 3-cycles, using the exact trace-based count of A cubed divided by 3;
2. directed feed-forward loop occurrences, defined as ordered edges
   source-to-middle and middle-to-target plus source-to-target, with the
   occurrence counted once per ordered source/middle/target triple. The
   implementation must document how reciprocal extra edges are handled.

Report observed count, null mean and sample SD, observed-minus-null delta,
standardized delta using the null SD when nonzero, and the full null draws.
This is a descriptive enrichment screen; no p-value gate is preregistered.

## Controls and failure policy

Run one smoke null only as an execution check; smoke is not evidence. Validate
node count, edge count, degree sequences, self-loop count, duplicate count,
and that raw and derived graph files are untouched. Refuse to overwrite any
existing artifact. If the graph or null violates the frozen constraints,
classify INVALIDATED and stop the experiment.

Estimate CPU/RAM before the full run. One process only. Keep every null draw
incrementally. Do not convert motif enrichment into a function or novelty
claim without a new task protocol and prior-art review.

## Reproducibility

Write protocol/code/graph hashes, selected nodes, graph diagnostics, observed
counts, all null counts, and an immutable summary under
research/results/MOTIF-MINE-001/FULL_<timestamp>_<gitsha>. Record the exact
algorithm and RNG seeds.
