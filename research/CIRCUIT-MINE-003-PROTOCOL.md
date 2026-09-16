# CIRCUIT-MINE-003 — degree-conditioned annotation null

Status: preregistered before metrics

## Question

Does the superclass-to-edge alignment observed in CIRCUIT-MINE-002 survive a null
that preserves each node's exact in-degree/out-degree pair and the global label
counts?

## Scope

This is a read-only structural adversarial check. It uses the existing derived
graph and annotations only. It does not read or write data/raw/ and does not
rebuild data/derived/graph/. Surviving degree-conditioned alignment is still
structural evidence, not evidence of biological function.

## Fixed measurements

- observed same-superclass directed-edge fraction;
- 20 null fractions;
- each null independently permutes superclass labels only within exact
  (in-degree, out-degree) strata;
- null mean, sample standard deviation and observed-minus-null delta;
- per-superclass observed internal-edge fraction and the corresponding
  degree-conditioned null mean.

The null preserves the graph, node degrees, label multiset, and exact degree-pair
stratum membership. No threshold is tuned after inspection.

## Decision rule

If alignment remains separated from the degree-conditioned null, retain a
structural modular/routing candidate for prior-art review and a task-specific
experiment. If it collapses, attribute the CIRCUIT-MINE-002 signal primarily to
degree structure and downgrade the candidate.

Neither outcome establishes a computational function. Any follow-up must include
a module-preserving or degree-preserving graph control, a positive control,
independent train/test data, matched parameters and measured compute.

## Compute and stop rule

One CPU job loads the existing derived edge arrays and annotation table. It may
scan existing derived files but may not touch raw data or protected graph
outputs. Record runtime and peak memory. Stop on memory pressure.

## Output

research/degree_conditioned_null_summary.json and the adversarial interpretation
in research/BREAKTHROUGH_CANDIDATES.md.
