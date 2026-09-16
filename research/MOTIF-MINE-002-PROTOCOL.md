# MOTIF-MINE-002 — block-preserving motif control

## Status

This protocol is frozen before MOTIF-MINE-002 metrics. It is a structural
control for the feed-forward candidate from MOTIF-MINE-001. It is not a
behavior, memory, biology, novelty, or ML-transfer claim.

## Question

Does the MOTIF-MINE-001 feed-forward occurrence enrichment survive a null that
preserves both directed degree sequences and superclass source-to-destination
block counts?

## Frozen graph and null

Use the exact read-only MaleCNS v1.0 500-node top-out-degree induced subgraph
from MOTIF-MINE-001. Use binary directed adjacency, no self-loops, and no
parallel edges. Use superclass labels from the frozen neurons table only to
define blocks.

Generate exactly 20 block-preserving nulls. A null swaps destinations only
within the same source-superclass and destination-superclass block. This
preserves source out-degree, destination in-degree, total edge count, and the
multiset of superclass blocks. Use 20 accepted swaps per edge, independent
null RNG streams, and refuse any invalid null. The null does not preserve
reciprocity, motifs, or spatial/neuropil structure.

## Primary measurements

Use the exact MOTIF-MINE-001 algorithms:

1. directed 3-cycles: trace of A cubed divided by 3;
2. non-induced feed-forward occurrences: source-to-middle,
   middle-to-target, and source-to-target, counted once per ordered triple.
   Reciprocal extra edges do not disqualify an occurrence and can contribute
   additional ordered occurrences.

Report observed counts, all 20 null draws, null mean and sample SD, observed
minus null delta, and standardized delta. The prior degree-preserving result
remains an explicitly separate control; do not pool null families.

## Controls and interpretation

Run one smoke null as execution validation; it is not evidence. Validate node
count, edge count, in-degree, out-degree, self-loop, duplicate, and block-count
invariants for every null. If an invariant fails, classify INVALIDATED. A
surviving enrichment is still structural and may reflect unpreserved
reciprocity, spatial organization, motif overlap, or label definition. No
biological or ML claim is licensed.

## Compute and reproducibility

Estimate CPU/RAM before the full run. Run one process only. Write metadata,
observed counts, and one immutable JSON per null before the final summary under
research/results/MOTIF-MINE-002/FULL_<timestamp>_<gitsha>. Record protocol,
code, graph, selected nodes, labels, RNG seeds, and all invariants. Never
overwrite prior artifacts or protected graph data.
