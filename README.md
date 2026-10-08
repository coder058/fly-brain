# Fly Lab

**Does a real brain's wiring compute better than random wiring? An auditable test on
the fruit-fly connectome — 165,122 neurons, 25.6 M connections.**

[![tests](https://github.com/coder058/fly-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/coder058/fly-brain/actions/workflows/ci.yml)
· Python 3.12/3.13 · CPU-only · MIT (code) / CC-BY 4.0 (data)

![EXP-E1-OP result](figures/fig4_e1_op_result.png)

## In 60 seconds

- I turned the Janelia **MaleCNS v1.0** connectome into a spiking recurrent network and
  asked whether its wiring beats random graphs on a temporal classification task.
- My first result (connectome ≈ random ≈ 0.76) was **fake**: the readout was peeking at the
  stimulus, the network was silent, and the "random" control silently deleted 8% of the
  brain. I found and fixed all of it, and the honest answer became a **negative**.
- Three weeks later I audited the negative the same way and found **two more bugs, both biased
  against the connectome**: one gain setting reused across inputs it did not fit (seed 9 ran
  at 1% of target activity), and a 48-neuron readout that missed the few hub neurons
  carrying the signal (seed 5: 20,231 spikes, 18 seen).
- Instead of quietly re-running until it looked good, I **preregistered** the fix, pushed it
  to GitHub, and only then ran it on 24 seeds nobody had seen.
- **Result:** the instrument got ~5× more precise, and the negative got *sharper*. The
  connectome beats random graphs (+0.081, 95% CI [+0.063, +0.100]) — but **loses to a
  random graph with the same degree sequence** (−0.036 [−0.057, −0.016]). Its advantage
  comes from *which neurons are hubs*, not from *how they are wired together*.

Full story: **[docs/CASE_STUDY.md](docs/CASE_STUDY.md)**.

## Why I built this

Connectomes are now complete enough to download as graphs, and "brain-inspired
architecture" is an easy claim to make and a hard one to test. I wanted to find out what it
actually takes to answer *"is this structure useful?"* without fooling myself — because in
ML and science alike, the expensive mistakes are the convincing results that come from
the measuring instrument rather than the thing being measured. This project is my practice
ground for that: real data at scale, strong null models, positive controls, preregistration,
and the willingness to publish an answer I did not want.

## Try it (no 1 GB download needed)

```bash
git clone https://github.com/coder058/fly-brain && cd fly-brain
pip install -r requirements.txt matplotlib
python -m flylab.demo           # ~30 s: reproduces each bug on real connectome data, writes figures/
python -m pytest -q             # 90+ tests
```

The demo runs on [`data/e1_slice/`](data/e1_slice), the exact 500-neuron slice every
experiment used (70 KB, SHA-256 checked, tested equal to the extraction from the full graph).

Reproduce the headline experiment (≈ 20 min on 4 cores):

```bash
python experiments/harness/e1_operating_point.py --seeds 1000:1024 --label confirmatory
```

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
| ![probe coverage](figures/fig3_probe_coverage.png) | **A readout looking the wrong way.** At equal firing rate the connectome's activity runs through a handful of hubs; about 37 of 450 neurons carry it (a random graph: ~100), and 48 random probes see ~4 of them. Fixed by reading every non-input neuron. |

## Results

Preregistered in [`EXP-E1-OP/protocol.md`](experiments/results/EXP-E1-OP/protocol.md)
(commit `214c7c7`, pushed before the run). 24 fresh seeds, 20 draws of each null, firing
rate matched within ±15%. Accuracy on a 5-class task (chance 0.20):

| gain matching / readout | connectome | degree-preserving null | Erdős–Rényi null | connectome − degree null |
|---|---|---|---|---|
| global / 48 probes *(original)* | 0.754 (n=20) | 0.719 | 0.650 | +0.042 [−0.041, +0.126] |
| global / full | 0.877 | 0.892 | 0.785 | −0.015 [−0.037, +0.007] |
| per-seed / 48 probes | 0.712 (n=21) | 0.739 | 0.656 | −0.024 [−0.093, +0.044] |
| **per-seed / full** *(primary)* | **0.869** | **0.906** | **0.788** | **−0.036 [−0.057, −0.016]** |
| no network (input only) | 0.830 | | | |

Missing connectome seeds in the 48-probe rows were refused by the liveness guard: each had
11,870–18,306 non-input spikes, of which 6–198 reached the probes; they are listed in the result file.

**What it means.** On this task and slice, a connectome-shaped graph carries the signal
better than a random one, and the reason is its degree distribution. Holding degrees fixed,
the real wiring is slightly *worse*. With the original 48-probe readout the network was
worse than no network at all. With a full readout the connectome (+0.039 [+0.016, +0.063])
and the degree-preserving null beat the no-network baseline; the Erdős–Rényi null does not.

**What it does not mean.** It is one task, one simple neuron model and one 500-neuron,
hub-selected slice (0.3% of the CNS; inhibition-dominated; 243 of the 500 neurons have no confident transmitter prediction, so
their outgoing weights are zero). Nothing here is a claim about fly intelligence.

## Repository map

| path | what |
|---|---|
| [`flylab/`](flylab) | library: graph loading, LIF dynamics, nulls, spectral gain, the bundled slice, the demo |
| [`experiments/harness/`](experiments/harness) | experiment runners; [`e1_operating_point.py`](experiments/harness/e1_operating_point.py) is the headline |
| [`experiments/results/`](experiments/results) | append-only results, `<prefix>_<UTC>_<git rev>.json`, with protocols |
| [`reports/`](reports) | audits and errata ([`E1_audit_fixes.md`](reports/E1_audit_fixes.md), [`EXP_E1_OP.md`](reports/EXP_E1_OP.md)) |
| [`tests/`](tests) | unit tests for nulls, leakage, liveness, determinism, the slice and the 2×2 runner |
| [`RESEARCH_LEDGER.yaml`](RESEARCH_LEDGER.yaml) · [`SCIENTIFIC_CLAIMS.md`](SCIENTIFIC_CLAIMS.md) | every experiment ID and what may be claimed from it |
| [`research/`](research), [`anomaly/`](anomaly) | later exploratory tracks (motif mining, routing, anomaly detection); see the ledger for their status |
| [`docs/lab-notebook/`](docs/lab-notebook) | raw working notes from the experiment loop, kept for transparency |

Other experiments (memory, ignition, glutamate polarity, motif controls) are recorded in the
ledger with their outcomes — mostly instrument failures the harness refused to score. None
is a positive result.

## How this was built

Solo project on a 2-vCPU cloud VM, then a 4-core container; no GPU. AI coding assistants
were used as pair programmers and as adversarial reviewers — several of the bugs above
were found by asking one to audit the code line by line as hostilely as possible. Every
experiment was gated by a written protocol before it ran, and every number in this README
links to a result file in the repository.

## Data and license

Code: MIT. Data: [MaleCNS v1.0](https://male-cns.janelia.org/), Janelia FlyEM, CC-BY 4.0;
the files under `data/` are subsets of it. See [`data/README.md`](data/README.md).
