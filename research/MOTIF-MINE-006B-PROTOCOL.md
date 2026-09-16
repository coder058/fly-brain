# MOTIF-MINE-006B — efficient reciprocity-preserving closure control

## Status

This protocol is frozen before MOTIF-MINE-006B metrics. It is a structural
control, not a behavior, memory, biology, novelty, or ML-transfer claim.

## Question

Does the corrected non-induced feed-forward-loop enrichment survive a null that
preserves directed in/out degree, superclass source-to-destination blocks, and
the number of reciprocal edge pairs?

## Frozen graph

Use the same read-only MaleCNS v1.0 graph and exact 500-node top-out-degree
subgraph as MOTIF-MINE-005. Build unsigned edge presence from all graph edge
coordinates, retain UNKNOWN zero-weight edges as topology, remove self-loops
explicitly, and record 23,704 analyzed edges. No raw or protected derived graph
may be written.

## Null construction

Generate 20 nulls with seeds 0..19. Decompose the graph into single directed
edge units and reciprocal two-edge units. For each identical source/destination
superclass block among single units, repeatedly propose a random permutation of
the destinations among the fixed sources. For each ordered superclass-pair
class among reciprocal units, repeatedly propose a random permutation of partner
endpoints while retaining both directions of every pair.

Accept 20 valid permutation rounds per group. Reject a proposal if it creates a
self-loop, duplicate, collision, or a new/lost reciprocal relation. A bounded
200-attempt cap applies per round and is recorded; inability to complete a
group is a null-generation failure, not a negative. This construction preserves
node in/out degree, edge count, exact block counts, and reciprocal-pair count.
Do not pool this family with earlier nulls.

## Measurements and gate

Primary: non-induced directed feed-forward occurrences. Secondary: corrected
induced feed-forward triads and induced directed 3-cycles. Report observed
count, null mean, sample SD, delta, all draws, and invariants. No p-value gate
is preregistered. Smoke is one seed and is not evidence.

If non-induced enrichment remains, reciprocity alone did not explain it; spatial
and neuropil structure, unit selection, and annotation remain alternatives.
If it collapses, record the narrow conclusion that reciprocal closure explains
the tested non-induced signal under this null. Neither outcome licenses a
biological or ML claim.

## Reproducibility

Estimate CPU/RAM before full. Run one process only. Write immutable protocol,
runner, hashes, smoke, sizing, null checkpoints, and summary under
research/results/MOTIF-MINE-006B/FULL_<timestamp>_<gitsha>. Never overwrite
earlier artifacts or touch raw/protected graph data.



## Algorithm audit correction

The initial smoke implementation was too strict for one block group and failed
closed before producing null metrics. The corrected pre-full implementation
tries randomized cyclic rotations of a group permutation. If no non-identity
rotation is valid within the bounded cap, it records a rigid/no-op round
explicitly; the current arrangement is already invariant-valid. The full
summary must expose nontrivial versus rigid rounds. This is an engineering
correction before evidence, not a post-hoc metric change.

## Performance correction

The prior pre-full smoke implementation enumerated every rotation for each
group and was stopped before metrics because it was quadratic in group size.
The current implementation samples bounded random cyclic offsets per round,
then records a rigid/no-op round when no offset is valid. This is an execution
optimization before evidence; invariants and the 20-round target are unchanged.

## Implementation audit correction

The previous smoke versions copied the complete edge set on each candidate
check and were stopped before evidence. The current implementation removes the
active group once per round and checks candidates against the remaining set,
without changing the null definition or invariant gate. This is a performance
correction before metrics; failed smoke artifacts remain immutable.
