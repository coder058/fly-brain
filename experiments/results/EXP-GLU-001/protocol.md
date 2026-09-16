# EXP-GLU-001 — glutamate polarity sensitivity

**Status: FROZEN before execution.** This is a polarity sensitivity experiment,
not a memory experiment and not a topology-advantage claim.

## Question

At the registered subgraph/task operating point, how sensitive are the
features and held-out classification readout to the treatment of predicted
glutamatergic synapses? Compare the shipped `glutamate_unknown` policy with
the explicit GluCl-alpha-like inhibitory and excitatory alternatives.

## Frozen design

- Dataset: the existing MaleCNS v1.0 selected `n=500` subgraph. The graph and
  `data/raw/malecns_v1/body-neurotransmitters-male-cns-v1.0.feather` are read
  only; no derived graph rebuild or raw write is allowed.
- Policies: `glutamate_unknown` (reference), `glutamate_inhibitory`
  (GluCl-alpha-like), and `glutamate_excitatory`. All non-glutamate signs use
  the registered neurotransmitter policy.
- Seeds: `0..11` (12 independent seeds). Each seed writes an immutable JSON
  checkpoint before the next seed starts.
- Task: the existing binary temporal classification task and its fixed
  train/test split generator; this experiment does not vary delay and does
  not claim memory.
- Readout: 48 probes, ridge sweep on train only, test evaluated once. If a
  policy fails liveness or rate matching, its readout metric is withheld.
- Trials: 60 per class, using the existing task configuration so the 12-seed
  run is not the historical 8-seed/40-trial underpowered artifact.
- Operating point: target non-input firing rate `0.002`; each policy and seed
  gets its own gain search over `[0.05, 80.0]`, inclusive. The bounds are a
  preregistered instrument cap inherited from the existing gain matcher, not
  fitted from test accuracy.
- Rate band: train and test realised rates must each be within 10% of target.
  This is an instrument convention, not a biological threshold.
- Liveness: check train and test features independently. A cell is valid only
  when both splits pass the existing `check_alive` guards and both rates are
  in band. Failed cells remain visible with reasons and are never scored.

## Gate and output

The primary output is the paired per-seed accuracy difference of inhibitory
and excitatory policies versus the unknown reference, with per-policy means
and 95% intervals only when all 12 seeds for every compared policy are valid.
If any required policy/seed is invalid, the comparative claim metric is
withheld and the invalid rows are reported. Zeroed-edge counts, effective
nonzero counts, gains, rates, and liveness are engineering measurements and
must not be presented as topology or profitability evidence.

No result from this experiment can reopen `E1_TOPOLOGY_ADVANTAGE`,
`EXP-006`, MEM-001, MEM-002, or the closed anomaly work. A negative or
incomplete polarity result is still a valid control outcome.

## Safety and provenance

Run on the 2-vCPU/15-GiB host only. Record wall time, CPU/RAM-safe execution,
protocol/runner/config/graph hashes, policy definitions, raw neurotransmitter
column, gain match diagnostics, liveness, rates, and missing reasons. The
runner must fail closed on provenance mismatch, write incrementally, and must
not overwrite any prior artifact or `EXP-INST-001/conclusion.json`.
