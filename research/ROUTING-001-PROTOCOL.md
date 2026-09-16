# ROUTING-001 — preregistered functional routing test

## Status

Protocol frozen before ROUTING-001 metrics. This is a mechanism test, not a
claim that the MaleCNS graph is a brain simulation.

## Question

Does the observed superclass-conditioned block structure support selective routing
of two independent input streams into their corresponding output compartments,
beyond degree-preserving rewiring and beyond a null that preserves the observed
source/destination superclass block counts?

## Biological structure -> computational operation -> task

- Structure: the frozen MaleCNS v1.0 signed graph and the 'superclass' labels in
  data/derived/graph/neurons.feather.
- Operation: sparse, compartment-conditioned communication.
- Task: four balanced patterns (A,B) in {0,1}^2. A pulse is delivered only to
  stream-A inputs when A=1 and only to stream-B inputs when B=1. Readouts use
  non-input probes from the corresponding two superclasses.
- Primary measurement: paired per-seed routing margin
  mean(within-channel binary accuracy) - mean(cross-channel binary accuracy).
  Within-channel means decode A from A probes and B from B probes; cross-channel
  means decode A from B probes and B from A probes. Readout hyperparameters are
  selected on train only.
- Falsification: if the connectome does not exceed the block-preserving control
  under the preregistered gate, the routing hypothesis is not supported.

## Fixed graph and arm construction

- Subgraph: exactly 500 nodes selected by descending out-degree, stable tie order,
  matching the existing E1 CPU-first selection rule. No metric is used for node
  selection.
- Labels: the two most represented 'superclass' values in that fixed subgraph,
  sorted by descending count then label. This deterministic rule is locked before
  task metrics; if either group has fewer than 48 eligible nodes, the task is
  INVALIDATED rather than re-tuned.
- Inputs: 16 eligible nodes per stream; probes: 32 non-input nodes per stream.
  Inputs are the highest out-degree eligible nodes and probes are the lowest
  out-degree eligible non-input nodes within each selected superclass. These
  counts are fixed for CPU cost and are not tuned to results.
- Arms:
  1. connectome_signed: observed signed weights and endpoints.
  2. degree_preserving: directed double-edge swaps, preserving both degree
     sequences, edge count, simplicity, and the weight multiset.
  3. block_preserving: endpoint swaps restricted within each
     (source_superclass, destination_superclass) block, preserving block counts,
     each source out-degree, edge count, simplicity, and the weight multiset.
- Every arm uses the same nodes, inputs, probes, task trials, readout dimension,
  and sparse operation count. degree_preserving and block_preserving are
  secondary/strong controls; the primary contrast is connectome vs
  block_preserving, with connectome vs degree_preserving reported separately.

## Dynamics, rate matching, and splits

- LIF parameters are the existing E1 parameters: dt=1, tau_m=6,
  v_rest=0, v_reset=0, v_th=1, r=1.
- Each trial has 32 steps. The input pulse occupies steps 0--3; later external
  current is zero. I_amp=6.0, inherited from the existing E1 task.
- Input noise SD is 0.20 on input nodes only. This is an uncalibrated task
  design value, locked before metrics; it is not a finding.
- 20 trials per pattern, 80 trials total. For every pattern, the first 14
  trials are train and the final 6 are test. Noise streams are deterministic
  and independent by seed/trial. Test labels are never used for decisions.
- Seeds: exactly 12 seeds, 0..11.
- For each arm and seed, gain is calibrated independently on separate
  8-trial calibration currents to a target non-input pool rate of 0.002,
  using gain range [0.05, 80.0], relative tolerance 0.15, and at most 24
  bisection iterations. If the target is outside the range, record that arm/seed
  as MISSING; do not silently substitute a gain.
- Calibration target is inherited from the validated instrument configuration;
  it is a rate-matching operating point, not a biological firing-rate claim.

## Positive control

Before interpreting any graph arm, run a known two-compartment routing graph
with direct A-input->A-probe and B-input->B-probe edges, same node count and
same task pipeline. It must be alive in both splits and have routing margin at
least 0.10. The 0.10 threshold is inherited from the existing instrument
minimum-effect gate and is locked before the run; it is not estimated from
connectome results. If this fails, ROUTING-001 is INVALIDATED and graph-arm
metrics are not interpreted.

## Liveness and validity

For each arm/seed, check train and test separately. An arm/seed is alive only
if non-input pool activity, A-probe activity, and B-probe activity are all
nonzero and the feature matrix has at least 10 unique rows and nonzero
variance. A dead arm/seed is MISSING, not a negative functional result.
Primary task validity requires all 12 connectome and block-preserving rows alive
and rate-matched. Degree-preserving rows are reported as secondary and do not
delete a valid primary pair, but any missingness is explicit.

## Predefined gate

The routing claim is SUPPORTED only if:

1. the positive control passes;
2. all primary connectome/block rows are alive and rate-matched;
3. the paired mean connectome-minus-block routing-margin difference is positive;
4. its two-sided paired t 95% CI excludes zero; and
5. the connectome mean routing margin is at least 0.10.

Otherwise classify the result as NOT_SUPPORTED, INCONCLUSIVE, or
INVALIDATED according to the liveness/CI rules. This gate does not establish
biological function, novelty, or ML transfer.

## Controls and alternative explanations

- Degree-preserving control tests whether routing is explained by node degree.
- Block-preserving control tests whether exact node-level wiring/weights add
  value beyond the observed superclass block counts.
- Same nodes/edges/weights/readout budget prevent trivial compute advantages.
- Alternatives remaining after a positive result: spatial/neuropil structure,
  sign/weight assignment, motif profile, annotation incompleteness, and task
  encoding. A positive result would require a new ablation/replication before
  any discovery or ML claim.

## Compute and failure policy

Planned main workload before implementation overhead is
3 arms x 12 seeds x 80 trials x 32 steps = 92,160 sparse LIF steps,
plus independent gain calibration. The estimated cost is not a measured runtime.
Smoke must run first. If sizing indicates more than approximately 4 hours or
RAM pressure on Ubuntu-1 (2 vCPU / 15 GiB), stop before the full run and record
the blocker; do not reduce seeds or change the task silently. One heavy process
at a time. Outputs are written incrementally to a new
research/results/ROUTING-001/ directory and never overwrite prior artifacts.

## Reproducibility

Record exact git SHA, graph metadata/hash references, protocol SHA256, code SHA256,
selected labels/nodes, arm diagnostics, gain/rate calibration, liveness,
per-seed metrics, paired differences, CI, and the final gate. No raw data or
derived graph files may be modified.

## Frozen implementation details

The degree-preserving arm uses the existing directed-null implementation with
20 accepted swap attempts per edge. The block-preserving arm uses 8 accepted
within-block swaps per edge; this fixed value is an engineering control setting,
not a tuned parameter. The smoke is exactly one seed and two trials per pattern,
and is not evidence. The positive control uses the same independent target-rate
gain calibration as graph arms.

## Smoke-only liveness detail

The full-run liveness gate requires at least 10 unique feature rows in each
split. Because the fixed smoke has one trial per pattern in each split, its
diagnostic threshold is 2 unique rows; this only tests execution and activity
paths and cannot pass the full evidence gate.

## Pre-full instrument repair after diagnostic smoke

The first two diagnostic smokes are preserved as non-evidence. They exposed two
instrument issues: signed spectral normalization put the connectome below the
target-rate ceiling, and degree-selected probes were silent in the
block-preserving null. Before any full metrics, the locked repair is:

- use the absolute spectral radius for gain normalization, matching the
  existing MEM-002/MEM-003 rate-matching convention; this is an operating-point
  repair, not a biological claim;
- select the first locked local node IDs as inputs and the next locked local
  node IDs as probes within each selected superclass, with no degree-based
  probe selection.

No full-run metric has been inspected yet. The original smoke outputs remain
unchanged and document the reason for this repair.

## Signed-state readout repair

The fixed-ID smoke showed that the A-channel connectome edges into the selected
probes were inhibitory/unknown rather than excitatory, so spike-only probe
liveness would discard a potentially routed signed response. Before full
metrics, the locked readout is changed to bin-mean membrane voltage at the
same probes. Non-input pool spikes remain required for network liveness, while
probe liveness is nonzero membrane-state variation in train and test. The same
state readout is applied to every arm and the positive control. This is an
instrument repair, not a topology result.
