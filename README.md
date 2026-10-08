# Fly Lab

**Does a real brain's wiring compute better than random wiring? An auditable test on the
fruit-fly connectome (165,122 neurons, 25.6 M connections): four preregistered experiments,
six bugs in my own instrument, and an answer I did not want.**

[![tests](https://github.com/coder058/fly-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/coder058/fly-brain/actions/workflows/ci.yml)
· Python 3.12/3.13 · CPU-only · MIT (code) / CC-BY 4.0 (data)

![every preregistered comparison](figures/fig5_all_comparisons.png)

## In 60 seconds

- I turned the Janelia **MaleCNS v1.0** connectome into a spiking recurrent network and asked
  whether its real wiring carries a temporal signal better than random graphs.
- Every time I got an answer, I audited the instrument, and six times I found a bug that
  changed it: a readout peeking at the stimulus, a "random" control that deleted 8% of the brain, one gain setting reused across
  inputs it didn't fit, a readout watching the wrong neurons, a control that let 479 of 500
  neurons both excite and inhibit (biologically impossible — Dale's law), and a rate matcher
  too coarse for the connectome's trial-to-trial variability.
- Each fix was **preregistered and pushed to GitHub before it ran**, on seeds never used
  before. Along the way the connectome looked like it lost (−0.036), then like it won
  (+0.028, 95% CI [+0.008, +0.049]).
- **The final, preregistered answer is "not supported".** With every fix in place, on two
  disjoint 500-neuron slices: no detectable difference from a Dale-preserving rewiring on one
  (+0.004 [−0.014, +0.022]), clearly worse on the other (−0.116 [−0.163, −0.069]). Even its
  solid lead over a random graph on slice A (+0.08, three times) reverses on slice B (−0.05).

What this project demonstrates is not a discovery about flies. It is a measurement pipeline
that kept catching its own convincing results — including the one I was hoping for.

Full story: **[docs/CASE_STUDY.md](docs/CASE_STUDY.md)**.

## Why I built this

Connectomes are now complete enough to download as graphs, and "brain-inspired architecture"
is an easy claim to make and a hard one to test. I wanted to find out what it actually takes to
answer *"is this structure useful?"* without fooling myself — because in ML and science alike,
the expensive mistakes are the convincing results that come from the measuring instrument
rather than the thing being measured. This project is my practice ground for that: real data at
scale, strong null models, positive controls, preregistration, and publishing the answer the
data gives.

## Try it (no 1 GB download needed)

```bash
git clone https://github.com/coder058/fly-brain && cd fly-brain
pip install -r requirements.txt matplotlib
python -m flylab.demo           # ~30 s: reproduces the bugs on real connectome data, redraws every figure
python -m pytest -q             # ~100 tests
```

The demo runs on [`data/e1_slice/`](data/e1_slice): the exact 500-neuron slices the experiments
used (70 KB and 38 KB, SHA-256 checked; the main one is tested equal, edge for edge, to the
extraction from the full graph).

Reproduce any experiment with the command in its protocol (≈ 20–35 min each on 4 cores). A fresh
clone reproduced all 3,960 result rows of EXP-E1-OP exactly; rebuilt from raw data on another
machine, the original September run reproduced to every digit.

Rebuild everything from Janelia's raw files (≈ 5 min, 16 GB RAM):

```bash
python scripts/download_malecns.py                       # 1.1 GB, SHA-256 verified
python scripts/build_graph.py --out-dir data/derived/graph_check
# -> 165,122 neurons, 25,563,197 connections, 124,025,046 synapses (matches the record exactly)
```

## What the bugs looked like

| | |
|---|---|
| ![null bug](figures/fig1_null_bug.png) | **The null that wasn't.** Shuffling connection endpoints and rebuilding a sparse matrix lets SciPy merge duplicates: 8% of connections vanish. Replaced by a directed double-edge swap that preserves every degree exactly ([`flylab/nulls.py`](flylab/nulls.py)). |
| ![rate spread](figures/fig2_rate_spread.png) | **One gain for every input.** Each seed drives a different 10% of neurons. A random graph doesn't care; the hub-heavy connectome swings from 0.1× to 3.3× the target activity. Fixed by matching activity per seed. |
| ![probe coverage](figures/fig3_probe_coverage.png) | **A readout looking the wrong way.** At equal firing rate about 37 of 450 neurons carry the connectome's activity (a random graph: ~100), and 48 random probes see ~4 of them. Fixed by reading every non-input neuron. |
| | **A control that broke Dale's law.** The degree null's weights followed the receiving neuron, not the sender, so 479 of 500 neurons ended up both exciting and inhibiting. Same edges, weights kept on the sender: the null loses 5 points on 24/24 seeds ([`weights_follow="pre"`](flylab/nulls.py)). |
| | **A matcher too coarse for the connectome.** Gain was tuned on 20 trials to ±15%; on slice B the connectome's full-set rate then landed at 0.7×–4.4× of target and 11/24 seeds were lost. Matching on all training trials to ±5% lost 1/24. |

## Results

Every confirmatory comparison, preregistered, 24 fresh seeds each, 20 draws of every null,
firing rate matched per seed (±15%), full non-input readout. Accuracy on a 5-class task
(chance 0.20). Paired difference connectome − control, 95% CI.

| experiment | slice | vs Erdős–Rényi | vs degree null (mixes signs) | vs degree null (Dale's law kept) |
|---|---|---|---|---|
| [E1-OP](reports/EXP_E1_OP.md) | A | +0.081 [+0.063, +0.100] | −0.036 [−0.057, −0.016] | — |
| [E1-DALE](reports/EXP_E1_DALE.md) | A | +0.101 [+0.080, +0.123] | −0.021 [−0.045, +0.002] | +0.028 [+0.008, +0.049] |
| [E1-REPL](reports/EXP_E1_REPL.md) | B | *instrument incomplete (13/24 seeds)* | | |
| [**E1-MATCH**](reports/EXP_E1_MATCH.md) (final) | **A** | **+0.080 [+0.060, +0.099]** | — | **+0.004 [−0.014, +0.022]** |
| [**E1-MATCH**](reports/EXP_E1_MATCH.md) (final) | **B** | **−0.051 [−0.098, −0.004]** | — | **−0.116 [−0.163, −0.069]** |

Slice A: the 500 highest out-degree neurons. Slice B: neurons ranked 501–1000, disjoint.
A no-network baseline (linear readout of the raw input) scores 0.83–0.84; the connectome beats
it on slice A (+0.033 [+0.012, +0.055]) and falls below it on slice B (−0.092 [−0.138, −0.045]).

**What it means.** On this task and neuron model, there is no evidence that the fly's specific
wiring carries the signal better than a rewiring with the same degrees, weights and signs. Its
advantage over a fully random graph is real on one slice and reversed on another, so it is a
property of *which* neurons you take, not of fly wiring in general.

**What it does not mean.** That connectome wiring is useless. One simple task, a leaky
integrate-and-fire model with synapse counts as weights, and two hub-selected slices of 500
neurons (0.3% of the CNS each) is a narrow probe; on slice A, 243 of 500 neurons have no
confident transmitter prediction and send zero-weight outputs.

How much each instrument fix mattered on slice A is shown in the
[EXP-E1-OP 2×2](reports/EXP_E1_OP.md) and in
[`figures/fig4_e1_op_result.png`](figures/fig4_e1_op_result.png).

## Repository map

| path | what |
|---|---|
| [`flylab/`](flylab) | library: graph loading, LIF dynamics, nulls, spectral gain, bundled slices, the demo |
| [`experiments/harness/`](experiments/harness) | runners; [`e1_operating_point.py`](experiments/harness/e1_operating_point.py) runs every preregistered experiment |
| [`experiments/results/`](experiments/results) | append-only results with their protocols (`EXP-E1-OP`, `-DALE`, `-REPL`, `-MATCH`) |
| [`reports/`](reports) | audits, errata and one report per experiment |
| [`tests/`](tests) | unit tests for nulls (both weight conventions), leakage, liveness, determinism, slices and the runner |
| [`RESEARCH_LEDGER.yaml`](RESEARCH_LEDGER.yaml) · [`SCIENTIFIC_CLAIMS.md`](SCIENTIFIC_CLAIMS.md) | every experiment ID and what may be claimed from it |
| [`research/`](research), [`anomaly/`](anomaly) | earlier exploratory tracks (motif mining, routing, anomaly detection); see the ledger |
| [`docs/lab-notebook/`](docs/lab-notebook) | raw working notes from the experiment loop, kept for transparency |

Other experiments (memory, ignition, glutamate polarity, motif controls) are recorded in the
ledger with their outcomes — mostly instrument failures the harness refused to score. None is a
positive result.

## How this was built

Solo project on a 2-vCPU cloud VM, then a 4-core container; no GPU. AI coding assistants were
used as pair programmers and as adversarial reviewers — several of the bugs above were found by
asking one to audit the code line by line as hostilely as possible. Every experiment was gated
by a written protocol pushed before it ran, and every number in this README comes from a result
file in the repository.

## Data and license

Code: MIT. Data: [MaleCNS v1.0](https://male-cns.janelia.org/), Janelia FlyEM, CC-BY 4.0; the
files under `data/` are subsets of it. See [`data/README.md`](data/README.md).
