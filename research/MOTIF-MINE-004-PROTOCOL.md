# MOTIF-MINE-004 — corrected unsigned-edge motif inventory

## Status

This protocol is frozen before MOTIF-MINE-004 metrics. It corrects the prior
edge-presence audit. It is a structural mechanism screen, not a behavior,
memory, biology, novelty, or ML-transfer claim.

## Question

On the full unsigned edge topology of the fixed 500-node subgraph, are
directed feed-forward occurrences or induced feed-forward/cyclic triads
enriched beyond degree-preserving and superclass-block-preserving nulls?

## Frozen graph

Use the read-only MaleCNS v1.0 graph and the exact 500-node top-out-degree
subgraph. Build binary directed edge presence from the graph edge coordinates,
not signed weights; UNKNOWN zero-weight edges remain present. Remove
self-loops explicitly and record the resulting edge count. No parallel edges
are allowed.

## Nulls

Generate 20 degree-preserving and 20 superclass source-to-destination
block-preserving nulls, seeds 0..19, with 20 accepted swaps per edge. Preserve
the node set, edge count, directed in-degree, directed out-degree, and for the
block family the superclass block multiset. Do not pool null families. No
result is used to change the subgraph or null settings.

## Measurements

Count three quantities for the observed graph and every null:

1. non-induced feed-forward occurrences: top-to-middle, middle-to-sink, and
   top-to-sink; reciprocal extra edges do not disqualify an occurrence;
2. induced feed-forward triads: exactly those three single-direction edges and
   no reverse edge on any pair;
3. induced directed 3-cycles: exactly one directed edge on each pair, counted
   once per cycle and excluding reciprocal pairs.

Use explicit integer adjacency enumeration, not boolean sparse matrix powers.
Report all draws, null mean, sample SD, delta, and standardized delta. No
p-value gate is preregistered.

## Failure policy and reproducibility

Smoke uses one draw per null family and is not evidence. Fail closed on any
invariant violation. Estimate CPU/RAM before the full run. Write protocol,
code, graph hashes, selected nodes, observed counts, all immutable checkpoints,
and summary under research/results/MOTIF-MINE-004/FULL_<timestamp>_<gitsha>.
Never touch raw data or rewrite prior artifacts. No functional, biological,
novelty, or ML claim is allowed from this structural screen alone.
