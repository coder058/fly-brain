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

## CIRCUIT-MINE-003 — degree-conditioned annotation alignment

- Observation: Same-superclass edge fraction was 0.7215534504545734. Twenty exact-(in-degree, out-degree)-stratified label permutations had mean 0.5091055805735097 and sample SD 0.0009599352346649315; observed-minus-null mean was 0.21244786988106368.
- Possible mechanism: Broad annotation blocks retain connectivity alignment beyond the tested degree-pair structure.
- Alternative explanations: Exact degree pairs do not control spatial proximity/neuropil, sign or weight, motif profile, annotation completeness, or the fact that superclass is an anatomical label. The statistic is one edge-block measure.
- Fastest discriminating test: A preregistered two-stream routing task using observed blocks versus degree-preserving and module-preserving graph controls, with matched edges/ops and an explicit positive-control routing graph.
- Strongest control: Preserve node degrees and graph size; add module-preserving and learned-sparse baselines; rate/parameter/compute match per seed.
- Potential ML abstraction: Annotation-conditioned sparse routing, only if the task effect survives functional controls.
- Potential application: Multimodal fusion or continual-learning interference control, only after task validation.
- Novelty status: UNVERIFIED; structural alignment alone is not a novelty claim.
- Confidence: STRUCTURAL_ONLY; no function or ML-transfer measurement yet.

## Adversarial review

- Leakage: no task labels or test metrics were used; this is descriptive graph analysis.
- Degree confounding: addressed by the exact degree-pair null, but not all anatomical/spatial confounds.
- Scope: one superclass edge statistic; no function, memory, topology advantage, or ML transfer is established.
- Decision: do not promote to discovery. Move to a task-specific routing test only after prior-art review.

## ROUTING-001 — functional routing, incomplete primary contrast

- Observation: Positive control passed 12/12. Connectome_signed was measured in 12/12 seeds with mean routing margin 0.2482638889. Degree-preserving was measured in 12/12 with mean -0.0052083333. Block-preserving was measured in 10/12; seeds 3 and 9 were MISSING because the fixed target-rate calibration remained below target at the gain ceiling.
- Possible mechanism: The observed wiring may support selective two-stream state routing beyond degree, but this is not established because the primary block comparison is incomplete.
- Alternative explanations: Operating-point ceiling, state-readout choice, task encoding, superclass labels, spatial/neuropil structure, sign/weight/motif structure, and finite test resolution.
- Fastest discriminating test: ROUTING-002 fixed gain-envelope calibration, no task metric, then a separately preregistered operating-point replication if a common reachable rate exists.
- Strongest control: Keep subgraph, labels, inputs, probes, seeds, edge/weight budget, and task fixed; vary only the predeclared calibration envelope.
- Potential ML abstraction: Conditional sparse routing remains UNSET pending a complete functional contrast.
- Potential application: Multistream interference control remains UNSET.
- Novelty status: UNVERIFIED; primary literature already covers anatomical organization and connectome-constrained computation.
- Confidence: INCONCLUSIVE / INSTRUMENT-LIMITED.

## Adversarial review

- Leakage: no test metric was used for gain selection; readout ridge was selected on train only.
- Positive control: passed all planned seeds; the measurement path can detect a known routing graph.
- Degree control: complete and near-zero margin, but it is secondary because the primary block null is incomplete.
- Block control: two seeds missing due rate ceiling; missing rows were not scored or dropped as negatives.
- Decision: no routing claim, no discovery, no ML translation. Resolve the calibration envelope first.

## ROUTING-002 — operating-point envelope

- Observation: On the frozen 9-point gain grid, the 0.002 ±15% reference target was reachable in connectome 0/12, degree-preserving 1/12, and block-preserving 5/12 seeds. Mean maximum grid rates were connectome 0.015227141203703706, degree 0.26948464765847574, block 0.1831652866809117.
- Possible mechanism: the signed connectome and controls occupy different rate envelopes under the shared LIF normalization.
- Alternative explanations: coarse grid resolution, discontinuous spiking, gain normalization, calibration-current choice, and finite 256-step calibration workload.
- Discriminating next test: a new task protocol with an operating point selected from this calibration envelope and independently rate-calibrated per arm/seed.
- Decision: calibration-only; no routing, topology, biology, or ML claim.

## ROUTING-003 — operating-point replication

- Observation: At target rate 0.013 ±15%, positive control 12/12, connectome 12/12, degree 12/12, block 8/12. The paired n=8 connectome-minus-block mean was -0.07031250000000004 with CI95 [-0.14872401153071557, 0.008099011530715503].
- Alternative explanation: block-preserving rate response is discontinuous or outside the frozen target envelope in four seeds.
- Decision: INCONCLUSIVE; no routing advantage or loss. Do not tune this ID further.
- Next mechanism: a structural directed-motif inventory with degree-preserving nulls.

## MOTIF-MINE-001 — feed-forward structural candidate

- Observation: On the fixed 500-node subgraph, observed directed 3-cycles = 85 and non-induced feed-forward occurrences = 62,611. Across 20 degree-preserving nulls: cycles 84.85 ±0.3663; feed-forward 25,254.5 ±237.19.
- Possible mechanism: higher-order triadic closure beyond in/out degree may create reusable feed-forward structure.
- Alternative explanations: reciprocal edge structure, superclass blocks, spatial/neuropil organization, non-induced counting, and the high-out-degree subgraph filter.
- Strongest next control: degree- and block-preserving rewires with the same node set and edge count.
- Decision: structural candidate only; no function, novelty, or ML translation.

## MOTIF-MINE-002 — enrichment beyond tested blocks

- Observation: FFL observed 62,611 versus block-preserving degree-matched null mean 36,682.15 ±280.39; residual delta 25,928.85. Cycles 85 versus 84.95 ±0.224.
- Possible mechanism: directed triadic closure remains after tested degree and superclass-block controls.
- Alternative explanations: non-induced counting, reciprocal edge dependence, spatial/neuropil structure, and the high-out-degree subgraph.
- Next discriminating test: induced FFL/cycle counts under both degree-preserving and block-preserving nulls.
- Decision: stronger structural candidate, still not function, novelty, or ML evidence.

## Motif audit correction

- The cycle submetrics from MOTIF-MINE-001/002 are invalidated because boolean sparse multiplication counted participating vertices, not cycle occurrences.
- FFL counts remain valid because they used dense integer adjacency.
- MOTIF-MINE-003 is the corrective induced-cycle/FFL measurement; no cycle claim is carried forward from the old artifacts.

## MOTIF-MINE-003 — induced control falsifies abundance candidate

- Observation: induced FFL 15,740 versus degree-null 18,953.1 ±267 and block-null 22,673.05 ±383.73; induced cycles 354 versus degree 1,734.15 ±78.59 and block 1,566.1 ±69.25.
- Interpretation: non-induced enrichment depended on reciprocal/extra edges; induced abundance is depleted under both controls.
- Decision: reject the tested reusable-FFL abundance candidate. This is not a biological negative or general topology verdict.
- Next: test signed polarity composition of induced FFLs, not motif abundance.

## Motif edge-presence audit correction

- MOTIF-MINE-001/002/003 are invalidated as full-topology analyses: boolean conversion of signed weights dropped UNKNOWN edges.
- Historical artifacts remain preserved; their FFL/cycle numbers are not claimable.
- Corrected test: MOTIF-MINE-004 uses unsigned edge presence, induced/non-induced definitions, and both null families.



## MOTIF-MINE-004 — mixed structural signature

- Result: non-induced FFL occurrences are above both tested null means, while induced FFLs and induced cycles are below both.
- Status: structural lead, not a breakthrough and not claim-ready.
- Why it matters: it separates extra-edge/reciprocal closure from exact induced triads on the corrected unsigned topology.
- Main risks: one fixed 500-node high-out-degree subgraph; no spatial/neuropil null; UNKNOWN edges are retained only as topology and are not interpreted as signs; no task or function readout.
- Next discriminator: SPECIALIZATION-001 full signed-composition screen.


## MOTIF-MINE-004 audit correction

M4's induced counter missed one reverse edge, so the induced values are not
claimable. The non-induced FFL result is separable but not a breakthrough.
MOTIF-MINE-005 is the fail-closed corrected replication; no induced conclusion
is carried forward until it completes.


## SPECIALIZATION-001 — sign composition

- Result: 33,551 induced FFLs; 1,303 all-positive and 11,359 any-inhibitory.
- Degree null: all-positive mean 441.6; block null: 2,707.1.
- Decision: sign composition is a structural pattern, but the tempting positive-only signal fails the block-preserving comparison.
- Risk: UNKNOWN edges and edge-attached signs may encode annotation/block effects; no functional readout exists.
- Status: not a breakthrough. Test reciprocity-preserving structure next.


## MOTIF-MINE-007B — residual structural lead

- Result: degree+reciprocity null means 240,957.95 non-induced FFLs, 23,621.65 induced FFLs, and 4,212.1 induced cycles.
- Observed: 490,588, 33,551, and 4,276 respectively.
- Interpretation: reciprocity explains much of the earlier contrast, but not all under this complementary null.
- Limitation: superclass blocks are broken; the residual is not yet attributable to a motif mechanism.
- Next: functional signed-weight comparison; no ML abstraction yet.


## MOTIF-FUNC-001 — first functional signal

- Result: observed-minus-degree+reciprocity-null routing margin mean 0.17614, 95% CI [0.14789, 0.20438], n=11 paired seeds.
- Gate: positive control 12/12; observed 12/12; null 11/12 with one calibration MISSING.
- Scope: valid only for this LIF readout and this broad null.
- Main risk: superclass/spatial organization and weight placement remain unseparated; this is not a biological or ML-transfer claim.
- Next: fixed-topology weight-permutation control.


## MOTIF-FUNC-002 — fixed-topology weight placement

- Observation: In the locked LIF readout, the observed signed-weight assignment exceeded a global permutation on the identical topology in 12 paired seeds; mean routing-margin difference 0.12847222222222224, 95% CI [0.08783645362404835, 0.16910799082039613].
- Mechanism licensed: signed-weight placement matters for this readout under this global permutation.
- Alternatives: coarse block/spatial weight allocation, edge-level weight placement, task encoding, and readout-specific effects.
- Decision: narrow functional PASS, not a biological, motif, novelty, or ML-transfer claim.
- Next discriminator: block-preserving weight permutation.


## MOTIF-FUNC-003 — within-block weight placement

**Invalidated:** this archived comparison used incorrect superclass blocks.
The historical bullets below are provenance only; see
[the erratum](../reports/MOTIF_FUNC_003_006_ERRATUM.md).

- Observation: The observed assignment exceeded a weight permutation constrained within each source→destination superclass block in 12 paired seeds; mean routing-margin difference 0.12847222222222224, 95% CI [0.08232979134020302, 0.17461465310424146].
- Mechanism licensed: coarse block weight composition alone did not explain the locked readout difference; within-block placement remains relevant under this control.
- Alternatives: sign-vs-magnitude effects, finer spatial/neuropil organization, edge-level structure, task encoding, and readout-specific effects.
- Decision: narrow functional PASS, not biological, motif, novelty, or ML-transfer evidence.
- Next discriminator: sign-versus-magnitude placement control.


## MOTIF-FUNC-004 — within-block sign placement

**Invalidated:** same block-label error; historical bullets are provenance only.

- Observation: Observed-minus-within-block sign-permuted margin was -0.029513888888888912, 95% CI [-0.06585597296303776, 0.006828195185259938], n=12; all liveness checks passed.
- Decision: INCONCLUSIVE. The interval crosses zero, so sign placement is neither accepted nor ruled out for this readout.
- Alternatives: magnitude placement, finer structure, task encoding, calibration/readout effects.
- Next discriminator: within-block magnitude-placement control.


## MOTIF-FUNC-005 — within-block magnitude placement

**Invalidated:** same block-label error; historical bullets are provenance only.

- Observation: 7 paired seeds were measured; 5 magnitude-arm seeds were MISSING from calibration. The 7-pair margin was 0.11309523809523805, 95% CI [0.05652894661576626, 0.16966152957470984].
- Decision: INCONCLUSIVE instrument-limited because the preregistered minimum n=8 was not met. Missing rows are not negatives.
- Next: one predeclared lower operating-point replication, then stop tuning this branch.


## MOTIF-FUNC-006 — lower operating-point replication

**Invalidated:** same block-label error; historical bullets are provenance only.

- Observation: At target 0.003, the magnitude arm measured 8/12 seeds; 4 were MISSING. The 8-pair margin was 0.08072916666666669, 95% CI [-0.03269711675051455, 0.19415545008384794].
- Decision: INCONCLUSIVE. The interval crosses zero; close this target-tuning branch.
- Next discriminator: independent stream-pair replication.


## MOTIF-FUNC-007 — cross-stream-pair replication

- Observation: On cb_intrinsic + visual_centrifugal, observed-minus-global-weight-permuted margin was 0.2239583333333333, 95% CI [0.18129871007072917, 0.2666179565959374], n=12; all liveness and invariants passed.
- Decision: Narrow functional replication PASS. It is not a biological, motif, novelty, or ML-transfer claim.
- Next discriminator: second cross-stream pair.


## MOTIF-FUNC-008 — second cross-stream-pair replication

- Observation: visual_centrifugal + ol_intrinsic yielded mean observed-minus-permuted margin 0.005208333333333333, 95% CI [-0.02011214196831266, 0.030528808634979324], n=12; all gates and invariants passed.
- Decision: INCONCLUSIVE. The M2/M7 effect is not universal across the tested stream pairs.
- Publication rule: expose M2-M8 artifacts, missingness, and null controls; do not market a universal topology or biological claim.
