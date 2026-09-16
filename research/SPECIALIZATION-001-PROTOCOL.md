# SPECIALIZATION-001 — signed polarity composition in induced FFLs

## Status

This protocol is frozen before SPECIALIZATION-001 metrics. It is a structural
specialization screen following the induced-motif abundance control. It is not
a behavior, memory, biology, novelty, or ML-transfer claim.

## Question

Among induced feed-forward triads, is the ordered sign composition of the three
forward edges structured beyond degree-preserving and superclass
source-to-destination block-preserving rewires?

## Frozen graph and nulls

Use the exact read-only 500-node top-out-degree induced subgraph with 9,469
directed edges. Retain edge presence separately from signed weight. Sign each
edge as positive, negative, or unknown when the frozen signed weight is greater
than zero, less than zero, or equal to zero.

Generate 20 degree-preserving nulls and 20 block-preserving nulls, seeds 0..19.
Preserve node set, edge count, directed in/out degree, and for the block family
the superclass source-to-destination block multiset. Attach each original edge
sign to its rewired edge record; unknown signs remain unknown. Do not pool null
families.

## Primary measurements

Use the induced feed-forward definition from MOTIF-MINE-003: exactly three
single-direction edges forming top-to-middle, middle-to-sink, and top-to-sink;
any reverse edge excludes the triad. For every triad, record the ordered
three-symbol polarity sequence along those three edges. Report full pattern
counts, null means and sample SDs, observed-minus-null deltas, and two
predeclared summaries: all-positive count and any-inhibitory count. Unknown
polarity is not treated as inhibitory.

## Controls and interpretation

Smoke uses one null from each family and is not evidence. Validate all graph
invariants and preserve every null checkpoint. No p-value gate is preregistered.
A sign-pattern difference is structural and may reflect annotation uncertainty,
weight assignment, reciprocity, block structure, or the null construction. No
claim about biological neurotransmission or computational function is licensed.

## Compute and reproducibility

Estimate CPU/RAM before the full run. Run one process only. Write protocol,
code, graph hashes, selected nodes, observed counts, all null draws and an
immutable summary under research/results/SPECIALIZATION-001/FULL_<timestamp>_<gitsha>.
Never overwrite earlier artifacts or protected graph data.


## Pre-full correction

Before the full run, an edge-presence audit found that the earlier 9,469-edge
description was the nonzero signed subset, not the full directed topology.
The runner already reads all graph edge coordinates; this protocol is corrected
before full metrics to make that scope explicit. The smoke is retained as
engineering-only and is not evidence. Full nulls must preserve 23,708 edge
records, directed in/out degree, and block counts; null self-loops must be zero.
UNKNOWN remains a topology edge and is not treated as inhibitory.