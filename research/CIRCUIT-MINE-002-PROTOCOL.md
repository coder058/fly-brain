# CIRCUIT-MINE-002 — annotation-conditioned block structure

Status: preregistered before metrics

## Question

Do the annotated superclass labels align with the directed edge structure more
than a node-label permutation null would predict, and is that organization
concentrated enough to motivate a routing or modular-computation hypothesis?

## Scope

This is a read-only structural analysis. It uses the existing derived graph and
the existing annotation table. It does not read or write data/raw/ and does not
rebuild data/derived/graph/. Alignment with annotations is not evidence of
function.

## Measurements fixed in advance

- edge fraction whose source and destination share a superclass;
- within-superclass edge fraction for every superclass represented in the graph;
- superclass sizes and directed edge counts;
- the observed same-superclass fraction versus 20 independent node-label
  permutations that preserve the graph and label counts;
- the largest strongly connected component size within each superclass with at
  least 100 nodes.

The 100-node reporting cutoff is a descriptive stability choice, not a
scientific gate. No group is removed from the aggregate same-label metric.

## Mechanism decision rule

A block-structure hypothesis survives scouting only if observed label alignment is
separated from the permutation null and at least one sufficiently sized group
has a distinct internal connectivity pattern. Otherwise modular/routing
hypotheses are downgraded and the queue moves to another mechanism family.

A positive structural alignment still requires a task-specific experiment with
a module-preserving null, a positive control, independent train/test data,
matched parameters and measured compute. It cannot be called a discovery.

## Compute and stop rule

One CPU job loads the existing sparse graph and annotation table. It may scan the
existing derived edge arrays but may not scan or write raw data. Record runtime
and peak memory. Stop if memory pressure approaches the host limit or a
protected path would be written.

## Output

research/annotation_block_summary.json and an interpretation update in
research/BREAKTHROUGH_CANDIDATES.md.
