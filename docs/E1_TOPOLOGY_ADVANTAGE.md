# E1_TOPOLOGY_ADVANTAGE

**Value:** `FALSE`

**Date (UTC):** 2026-09-15  
**Evidence:** `experiments/results/e1_null_ensemble_powered_20260915T130422Z_fe089d3.json`  
**Protocol:** 12 seeds × 60 trials/class × 20 null draws, rate-matched, leak-fixed harness.

connectome_signed did **not** beat ER / degree-preserving nulls (diff vs ER ≈ −0.017, 95% CI crosses 0).

This does **not** block Anomaly Detector V1. It means topology advantage is unproven under E1 reservoir classification — anomaly detection is a different task and must be evaluated on its own baselines + nulls.

## Follow-up (2026-10-08)

An audit found that the two chance-level connectome seeds (5 and 9) behind this result's wide
interval came from operating-point artifacts: gain matched on one seed's input map, and a
48-probe readout. This ID stays closed. The question was retested under a new preregistered
ID, [EXP-E1-OP](../reports/EXP_E1_OP.md): with both artifacts removed the direction holds and
sharpens — connectome − degree-preserving null = −0.036 [−0.057, −0.016] on 24 fresh seeds —
while the connectome beats Erdős–Rényi by +0.081 [+0.063, +0.100].
