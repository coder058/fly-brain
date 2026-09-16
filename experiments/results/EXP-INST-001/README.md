# EXP-INST-001

Instrument validation at the E1 measurement config (48 probes / rate 0.002 / signed / 12 x 60).

**Verdict:** PASS  
**INSTRUMENT_VALID_E1:** TRUE

Numbers below are from `stats.json` / `summary.json` of this run (`git_rev` 3dbe1d9).

## Gate

- target constructed effect (synthetic lock): 0.15
- predefined MIN_EFFECT: 0.10
- mean_diff (positive − null perm0): 0.36481481481481476
- ci95_diff: 0.11628726937451439
- ci_excludes_zero: true
- separated: true
- live seeds (spikes>0): 12 / 12
- empirical FP (19 null-perm gates): 0.0
- seed detection rate (positive, |Δ|≥0.10): 1.0
- seed FN rate (positive): 0.0
- seed false-detection rate (null pair): 0.0833
- null-pair mean_diff: 0.00185 (CI includes 0; separated false)
- no-injection mean acc: 0.6343
- positive mean acc: 1.0
- null perm0 mean acc: 0.6352
- sd of per-seed positive Δ: 0.2055
- realised mean rate: 0.00213
- PC-A (ignited−quiescent) mean_diff: 0.4435, separated true

## Residuals

- Positive arm at ceiling (acc=1.0 every seed). Realized Δ is larger than the 0.15 synthetic target. Alpha was not retuned.
- Seeds 5 and 9 have `dead_reason` but `alive=true` (pool_spikes>0). Seed 9: 306 spikes, no-injection acc=0.200.
- Stock ring-vs-ER PC-B not run. Injection is on features, after LIF.

## Interpretation

The E1 measurement procedure detected the pre-registered constructed effect under the predefined gate. This is not a topology result and does not reopen EXP-006.

## Next step

STOP. Do not launch EXP-E1B-001 from this runner.

Smoke is not evidence. Smoke status: ok.

See protocol.md, summary.json, stats.json, conclusion.json, provenance.json.
