# EXP-IGNITE-002 — polarity-assisted pair ignition

**Status: FROZEN before metrics.** This is the one permitted follow-up to
IGNITE-001. The new lever is the neurotransmitter polarity policy; this is not
a third input map, not a memory experiment, and not a topology-advantage
claim.

## Question

Can the same fixed instrument co-ignite under the shipped
`glutamate_unknown` connectome policy and the explicit GluCl-alpha-like
`glutamate_inhibitory` policy, using independent gains per policy and seed?

## Frozen design

- Dataset and map: the same selected `n=500` graph and the same deterministic
  protocol-hash-ranked 50-input/48-non-input-probe map used by IGNITE-001.
  `data/raw/` and committed `data/derived/graph/` remain read-only.
- Primary arms: `connectome_glutamate_unknown` and
  `connectome_glutamate_inhibitory`, built from the same traced subgraph and
  raw neurotransmitter lookup. The only changed lever is glutamate sign.
- Stimulus: existing cue generator with independent train/test inputs, cue at
  step 0 and zero external input afterward. No accuracy, AUC, classifier, or
  memory metric is computed.
- Gain grid: 16 logarithmically spaced values from `0.05` through `80.0`,
  inclusive. The upper value is the hard cap; no search beyond it.
- Target and band: target non-input firing rate `0.002`; both train and test
  rates for each policy/seed/gain must be within the already frozen IGNITE
  band of 20%. The band is not changed for this follow-up.
- Liveness: `check_alive` runs separately on train and test. Failed candidates
  remain `MISSING` with reasons; no failed row is silently dropped.
- Seeds and stages: smoke seed 0; sizing seeds 0, 1, 2; then 12-seed confirm.
  If sizing finds a pair, confirm only those gain values. If sizing finds no
  pair, confirm the full frozen grid once. No further map or polarity attempt
  is permitted after this ID.

## Gate and output

Each pair cell is `(seed, gain_unknown, gain_inhibitory)`. `pair_alive` is true
only when both policy arms pass train/test liveness and the rate band. Output
contains pair cells, gains, rates, sign counts, and resource timing. Accuracy
is always absent. If no pair is found, close as `NO_COIGNITE` and retain this
as an operating-point result only.

## Safety and provenance

Use a new append-only `ignite002_<UTC>_<git>/` directory. Record protocol,
runner, config, graph, policy, and raw-neurotransmitter-column hashes. Never
overwrite INST-001, previous MEM/GLU/IGNITE artifacts, `data/raw/`, or the
committed derived graph. Stop only for human STOP or the defined safety
blockers.
