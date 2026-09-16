# MOTIF-MINE-003 — induced motif control

## Status

This protocol is frozen before MOTIF-MINE-003 metrics. It is a structural
follow-up to MOTIF-MINE-001/002, not a behavior, memory, biology, novelty, or
ML-transfer claim.

## Question

Does the feed-forward enrichment persist when the motif is counted as an
induced directed triad, excluding reciprocal extra edges, under both
degree-preserving and degree-plus-superclass-block-preserving nulls?

## Frozen graph, nulls, and seeds

Use the exact read-only 500-node top-out-degree induced subgraph with 9,469
simple directed edges from the previous motif IDs. Use 20 degree-preserving
nulls and 20 block-preserving nulls, seeds 0..19. Preserve node set, edge
count, directed in-degree, directed out-degree, no self-loops, no duplicates,
and, for the block family, the superclass source-to-destination block
multiset. Do not pool the two null families. All nulls are generated with the
existing constructors and independent RNG streams.

## Induced measurements

An induced feed-forward triad has exactly three single-direction edges on
three nodes forming source-to-middle, middle-to-target, and source-to-target.
Any reverse edge on those three pairs excludes the occurrence. Each ordered
source/middle/target triple is counted once.

An induced directed 3-cycle has exactly one directed edge on each of the
three unordered node pairs, forming a cycle. Any reverse edge excludes the
occurrence. Each cycle is counted once, not once per starting node.

Report observed count, every null draw, null mean and sample SD, observed-minus-
null delta, and standardized delta for each motif and null family. No p-value
gate is preregistered. This remains a structural statistic.

## Failure and reproducibility

Smoke uses one draw from each null family and is not evidence. Fail closed on
any invariant violation. Estimate CPU/RAM before full execution. Write
metadata, observed counts, one immutable JSON per null and an immutable summary
under research/results/MOTIF-MINE-003/FULL_<timestamp>_<gitsha>. Keep raw and
derived graph files read-only. No function or ML interpretation is allowed
without a new protocol and prior-art review.
