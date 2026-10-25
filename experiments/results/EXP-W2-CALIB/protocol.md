# EXP-W2-CALIB — Does sugar → MN9 survive when MaleCNS is calibrated to FlyWire's excitability?

Status: **preregistered**. Committed and pushed before the runner is executed.

## Why

EXP-W1-SUGAR replicated Shiu et al.'s sugar → MN9 prediction on MaleCNS (MN9 95.4 Hz
[91.5, 99.3]; 0.0 Hz on three wiring nulls), but with the model's FlyWire-tuned weights about
20,500 MaleCNS neurons fire against ~490 on FlyWire. A post-hoc rescaling by the ratio of
median input synapses halved that spread but left it 22× too wide. So the replication shows the
pathway is *present*; it does not show that MN9 is *selectively* driven. If the response only
appears when most of the central brain is active, it is not the same prediction.

## Fixed choices

- Model: Shiu et al. defaults (`flylab.brain.DEFAULTS`). The only change is a gain `s`
  multiplying every recurrent MaleCNS weight. Input drive (Poisson kick `w_syn·f_poi`) is
  unchanged.
- Signs, input (LB3c, both sides, 23 neurons), output (mean of MN9_L and MN9_R): as in
  EXP-W1-SUGAR.
- **Calibration target: excitability only, never MN9.** Activity measure = mean over trials
  of the number of neurons that spike at least once in the trial, under LB3c at 200 Hz.
  FlyWire reference: the same measure on FlyWire 630 (unscaled), 4 trials.
- **Calibration:** geometric bisection of `s` over [0.05, 0.59], 8 evaluations, 4 trials
  each (MaleCNS activity is assumed to grow with `s`); the evaluated `s` with the smallest
  |log(activity / reference)| is used.
- Seeds: calibration trials (9000, k); confirmation trials (7100, k) — not used before;
  nulls (81000, d).

## Run

```
python experiments/harness/sugar_calibrated.py
```

## Primary endpoint

At the calibrated `s`, LB3c 200 Hz, 30 trials: mean MN9 rate with a two-sided 95% t-interval.
**"Survives calibration"** if the lower bound is > 10 Hz and the 0 Hz condition has mean
MN9 < 2 Hz. **"Does not survive"** if the upper bound is < 10 Hz. Otherwise "inconclusive".

## Secondary endpoints

1. Dose response: Spearman correlation of rate vs MN9 over 0, 50, 100, 150, 200 Hz.
2. MN9_L and MN9_R separately (MN9_R is incompletely traced; descriptive only).
3. Responder overlap with FlyWire, matched through MaleCNS `flywireType` (the method found
   post hoc in EXP-W1-SUGAR, now fixed in advance): of the 30 non-input FlyWire types with
   the highest rate under LB3c at 200 Hz (committed EXP-W1-SUGAR FlyWire run), how many map
   to MaleCNS types with neuron-weighted mean rate > 1 Hz; and the Spearman correlation over
   all mappable types active in either dataset. Reported next to EXP-W1-SUGAR's values
   (30/30, ρ = 0.10); a higher ρ means the calibrated response is more FlyWire-like.
4. Wiring control: three Dale-preserving degree nulls of MaleCNS, scaled by the same `s`.
   "Pathway depends on the wiring" if every null's MN9 mean is below the connectome's 95%
   lower bound.
5. Spread at the calibrated `s` (neurons that fire at all, and per trial) — reported, to
   check that calibration on 4 trials transfers to 30.

## What it can and cannot show

"Survives" would mean MaleCNS drives MN9 from sugar input even when the network is no more
excitable than Shiu et al.'s FlyWire model — a stronger replication than EXP-W1-SUGAR.
"Does not survive" would mean the MaleCNS replication depended on runaway excitation. Either
way, one global gain is a crude calibration; a mismatch in *where* activity goes would remain
visible in secondary 3.
