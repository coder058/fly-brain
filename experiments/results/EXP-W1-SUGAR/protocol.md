# EXP-W1-SUGAR — Does the sugar → MN9 prediction replicate on a second connectome?

Status: **preregistered**. Committed and pushed before any MaleCNS sugar simulation is run.
(FlyWire sugar simulations were already run in SHIU-REPRO to validate the simulator.)

## Background

Shiu et al. (Nature 634, 2024) built a whole-brain leaky integrate-and-fire model on the FlyWire
connectome and predicted that activating labellar sugar gustatory receptor neurons (GRNs)
drives MN9, the motor neuron for proboscis extension — a prediction they then confirmed in
flies. `flylab.brain` re-implements their model and is spike-for-spike identical to it in
Brian 2 (`tests/test_brain.py`); on their FlyWire table it reproduces their published
simulations (SHIU-REPRO: MN9 92.5 vs 93.3 Hz at 200 Hz; per-neuron r = 0.9998).

MaleCNS v1.0 is an independent reconstruction: a different (male) animal, a different lab and
pipeline, and a CNS that includes the ventral nerve cord. A model prediction that depends on
reconstruction details would not transfer; one that reflects the circuit should.

## Fixed choices

- Model: Shiu et al. defaults (`flylab.brain.DEFAULTS`), 30 trials × 1 s per condition.
- Signs: Shiu et al.'s rule (GABA, glutamate → −1; all other transmitters +1), applied to
  MaleCNS neuron transmitters (ground truth where available, else consensus).
- Input: cell type **LB3c**, the labellar GRN type FlyWire annotates "sugar" (Schlegel et al.
  2024); MaleCNS uses the same type names. All LB3c on both sides: 23 neurons in MaleCNS,
  30 in FlyWire 630. Note: 5 of Shiu et al.'s original 21 "sugar" GRNs are annotated in the
  later FlyWire release as LB3d (high salt), 4 as LB4b; LB3c-only input avoids that.
- Output: mean firing rate of MN9 (MaleCNS: mean of MN9_L and MN9_R; FlyWire: the MN9 used
  by Shiu et al.).
- Seeds: trial k uses RNG seed (7000, k). Nulls: stream (80000, d).

## Runs

```
python experiments/harness/sugar_mn9.py --connectome malecns --inputs lb3c_both,lb3c_L,lb3c_R \
    --rates 0,50,100,150,200 --null-draws 3 --label malecns
python experiments/harness/sugar_mn9.py --connectome flywire --inputs lb3c_both,shiu21 \
    --rates 0,50,100,150,200 --label flywire
```

Null draws are run for the first listed input (`lb3c_both`) only, at 200 Hz.

## Primary endpoint

MaleCNS, `lb3c_both`, 200 Hz: mean MN9 rate over 30 trials with a two-sided 95% t-interval.
**"Replicates"** if the lower bound is > 10 Hz **and** the 0 Hz condition has mean MN9 < 2 Hz.
**"Does not replicate"** if the upper bound is < 10 Hz. Otherwise "inconclusive".

## Secondary endpoints

1. Dose response (MaleCNS, `lb3c_both`): Spearman correlation between stimulation rate and
   MN9 rate over the five rates.
2. Laterality: `lb3c_L` and `lb3c_R` at each rate, MN9_L and MN9_R reported separately.
3. FlyWire comparator with the same LB3c-only input; and Shiu et al.'s original 21 inputs.
4. Cross-connectome responder overlap at 200 Hz: take the 30 non-input FlyWire cell types with
   the highest mean rate under `lb3c_both`; report how many have a same-named MaleCNS type
   with mean rate > 1 Hz under `lb3c_both`, and the Spearman correlation of type-mean rates
   over types present in both connectomes and active (> 0 Hz) in at least one.
5. **Wiring control:** three whole-brain Dale-preserving degree nulls of MaleCNS (every
   neuron keeps its in/out-degree, outgoing weights and transmitter sign; targets are
   permuted; the 101 autapses are dropped). "Pathway depends on the wiring" if every null
   draw's MN9 mean is below the connectome's 95% lower bound at 200 Hz.

## What it can and cannot show

A replication would mean the predicted sensorimotor pathway is a property of the fly's
circuit, robust to a different animal and reconstruction, under the same simple model. It
would not validate the model's dynamics beyond what Shiu et al. tested in flies. A failure
would mean the prediction is sensitive to reconstruction or annotation differences, which is
itself worth knowing before trusting single-connectome model predictions.
