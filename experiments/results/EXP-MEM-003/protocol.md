# EXP-MEM-003 — connectome versus DP memory curve

**Status: FROZEN before execution.** This protocol is the continuation after
MEM-002's instrument-incomplete result. It does not reopen MEM-001 or MEM-002.
It tests a primary connectome-versus-degree-preserving (DP) contrast; it does
not claim to model a biological fly brain.

## Question and hypothesis

Does useful memory degrade as cue delay increases under a controlled compute
and rate budget, and does the connectome differ from its degree-preserving
null? The directional hypothesis is deliberately non-directional: the
connectome may be higher, lower, approximately equal, or have a different
curve shape than DP. A valid negative result is informative.

## Frozen design

- Dataset: the existing MaleCNS v1.0 derived graph and selected `n=500`
  induced subgraph. `data/raw/` and the committed
  `data/derived/graph/` artifacts are read-only; no graph rebuild is allowed.
- Primary arms: `connectome` and degree-preserving `dp`.
- Secondary arms: `weight_perm`, `er`, and `ring`. A missing secondary cell
  does not remove a delay from the primary curve.
- Input map: deterministic top-50 nodes by positive active **incoming-edge
  count**, ties by local index, alternated between cue 0 and cue 1. This map
  is fixed before execution and is neither top-positive-outdegree nor
  positive-weight-sum. It is an instrument choice, not a performance-tuned
  feature map. If no primary pair is obtained, one and only one pre-registered
  fallback map is allowed: deterministic hash-ranked local nodes, first 50,
  with the same cue alternation.
- Delays: `10, 25, 50, 100, 250, 500` simulation steps. The cue is present
  only at step 0; later external-current values are zero. If sizing projects
  more than roughly four hours on this 2-vCPU/15-GiB host, the protocol is
  recut before metrics to the largest prefix of delays that fits and the
  recut is recorded before the run.
- Seeds: `0..11` (12 independent seeds), with incremental per-seed/per-delay
  JSON writes in a new run root. No test tuning or overwriting of prior
  MEM-002 artifacts is permitted.
- Trials: 10 trials per class per split (`train` and `test` generated
  independently). Smoke is one seed, delays 10 and 100, two trials per
  class, and is not evidence.
- Gain: independently calibrated for every arm and seed at reference delay
  100 using 64 logarithmically spaced candidates from `0.125` through
  `64.0`; `64.0` is the pre-registered gain cap inherited from the MEM-002
  instrument design. The selected gain is locked across all delays for that
  arm and seed. A gain beyond the cap is not tried.
- Rate matching: use live calibration candidates and choose the target that
  minimizes worst relative error across the available arms, ties by mean
  relative error then lower target. Select each arm's nearest live candidate.
  A cell is rate-matched only within a 10% relative band. This is an
  instrument convention, not a biological threshold. Primary connectome and
  DP are evaluated independently; secondary-arm missingness cannot change
  the primary eligibility decision.
- Liveness: run `check_alive` separately on train and test. A primary cell is
  eligible only when that arm passes both split liveness checks and both
  realised rates are within the locked calibration band. Failed cells remain
  `MISSING` with their reason; “Fly lost” is not an allowed interpretation.
- Controls: retain the registered connectome, DP, fixed-topology weight
  permutation, ER, and ring constructions. Do not drop a control post-hoc.

## Curve output and gate

For each eligible delay, compute the pre-registered memory readout separately
for connectome and DP on held-out test trials, with the same labels and trial
counts. The primary output is the delay-to-readout curve for each primary arm
and the paired contrast at each eligible delay; report per-seed values and
aggregate uncertainty. Accuracy/AUC is withheld for any cell that fails
liveness or rate matching. Secondary arms are reported where live, but never
gate the primary curve.

At least three delays with live, rate-matched connectome and DP cells are
required for an interpretable curve. Fewer than three is `INCONCLUSIVE`; no
directional claim is allowed. If there is no primary pair at any delay, run
the fallback input map exactly once. If it still yields no pair, record
`MEM_003_NO_PAIR`, update the ledger/claims/roadmap, and move to the
pre-registered polarity experiment `EXP-GLU-001`; do not run EXP-A-001 on a
missing memory instrument.

## Pre-run safety and provenance

Before the full job: run smoke, estimate runtime/RAM from the smoke, and
stop before metrics if the four-hour estimate or memory safety limit is
exceeded. Every artifact records protocol/runner/config hashes, graph hashes,
git revision, map rule, gains, liveness, rate matching, and missing reasons.
The runner must fail closed on provenance mismatch, write incrementally, and
never touch `data/raw/`, clobber `data/derived/graph/`, or overwrite
`EXP-INST-001/conclusion.json`.
