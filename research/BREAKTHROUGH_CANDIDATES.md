# Breakthrough candidates

No candidate is accepted before a measured observation, an alternative
explanation, a discriminating test, a strong control, and a prior-art check.

## CIRCUIT-MINE-001 — widespread recurrence, no compact core

- Observation: 163397 of 165122 nodes are in the largest strongly connected component; 3819936 reciprocal pairs were measured across the graph; reciprocal directed edges were 0.2988661 of graph edges.
- Possible mechanism: No mechanism accepted. The measured structure is widespread recurrence, not a localized recurrent circuit.
- Alternative explanations: The graph representation may merge anatomical regions; structural recurrence may still contain meaningful subcircuits at another scale.
- Fastest discriminating test: Annotation-conditioned block-structure analysis.
- Strongest control: Node-label permutation preserving graph edges and label counts.
- Potential ML abstraction: UNSET
- Potential application: UNSET
- Novelty status: UNVERIFIED
- Confidence: STRUCTURAL_ONLY

## CIRCUIT-MINE-002 — annotation alignment

- Observation: Same-superclass edge fraction was 0.7215534505; the 20 label-permutation null mean was 0.3435372246 with sample SD 0.0012592195.
- Possible mechanism: Annotated regions may correspond to graph modules or communication compartments.
- Alternative explanations: Region labels may correlate with degree structure; annotation may encode the same anatomical grouping being measured; the metric is only one block statistic.
- Fastest discriminating test: CIRCUIT-MINE-003 exact-degree-conditioned label null.
- Strongest control: Permute labels within exact (in-degree, out-degree) strata.
- Potential ML abstraction: UNSET
- Potential application: Conditional routing or interference control, only if a task survives controls.
- Novelty status: UNVERIFIED
- Confidence: STRUCTURAL_ONLY_PENDING_ADVERSARIAL_REVIEW

No task, memory, function, novelty or ML-transfer measurement has been made.
