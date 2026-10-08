# When the nulls are honest: auditing a fly-brain reservoir computer

*Case study — Fly Lab, September–October 2026*

## The question

The FlyEM team at Janelia has released a complete wiring diagram of an adult male
fruit-fly central nervous system, brain and nerve cord together (MaleCNS v1.0). Keeping
only fully traced neurons gives 165,122 neurons, 25.6 million directed connections and
124 million synapses — an entire nervous system you can download as a graph.

That invites an engineering question that is easy to ask and hard to answer honestly:

> **If you run a real brain's wiring as a recurrent neural network, does its structure
> compute better than random wiring with the same statistics?**

The "random wiring" part is where most of the difficulty lives. A connectome differs from a
random graph in many boring ways — its size, degree distribution, weight scale, sign
balance, how excitable it is — and any one of them can produce a "win" or a "loss" that says
nothing about structure. So the project became, in practice, a project about building an
instrument that cannot fool itself, and then checking whether it had.

## What I built

- **Data pipeline.** Hash-locked download of the three MaleCNS v1.0 files, a streaming
  builder that keeps only traced-to-traced connections and signs each one by the
  presynaptic neuron's predicted transmitter (acetylcholine +, GABA/histamine −, unknown 0).
  On a clean machine it reproduces the recorded totals exactly:
  165,122 neurons, 25,563,197 connections, 124,025,046 synapses.
- **Simulator.** Leaky integrate-and-fire dynamics on sparse signed matrices, CPU only.
- **Task.** Five classes of noisy temporal pulse patterns are injected into a random 10% of
  neurons; a ridge readout on binned spiking of the *other* neurons must name the class.
- **Controls.** A degree-preserving null (directed double-edge swap, exact in- and
  out-degrees, weights travel with their presynaptic neuron), an Erdős–Rényi null with the
  same edge count, a parameter-matched MLP, a no-network baseline, and a positive control
  (ring lattice vs random graph) the instrument must pass before any comparison counts.
- **Discipline.** Preregistered protocols, append-only results named
  `<prefix>_<UTC>_<git rev>.json` with harness and config hashes, liveness gates that
  refuse to score a silent network, and 90+ unit tests for the pieces most likely to lie.

## Round 1: the first number was fake

The first pipeline reported connectome 0.76, ER 0.76, shuffle 0.77, MLP 0.87. An
adversarial line-by-line audit found that none of it measured structure:

| bug | effect |
|---|---|
| Probe neurons included driven inputs | the readout was decoding the stimulus; with the leak removed every arm fell to **exactly chance (0.200)** |
| Default gain left the network silent | 0 useful non-input spikes; the "liveness" guard only checked feature variance, which the leak satisfied |
| "Degree shuffle" rebuilt a sparse matrix from permuted endpoints | SciPy sums duplicate entries: **7.9% of connections silently vanished** and self-loops appeared |
| One hand-tuned gain for every graph | the arms ran at effective gains **49× apart** |
| 5 seeds × 20 trials | the positive control *failed* at these settings: a real +0.15 effect measured as −0.03 ± 0.19 |

Each was fixed and tested ([`reports/E1_audit_fixes.md`](../reports/E1_audit_fixes.md)).
Gain became a controlled variable via spectral normalisation, then arms were matched on
firing rate instead, because equal spectral radius still left 50× activity differences.

## Round 2: an honest negative

With the instrument repaired, a powered run (12 seeds × 60 trials/class × 20 null draws,
rate-matched) gave:

| arm | accuracy |
|---|---|
| connectome | 0.634 ± 0.122 |
| degree-preserving null | 0.685 ± 0.030 |
| Erdős–Rényi null | 0.651 ± 0.017 |

No advantage; intervals cross zero. It was written up as a negative result, and the follow-up
memory and ignition experiments that tried to find a better operating point ended as
`NO_PAIR` / `NO_COIGNITE` — the instrument refused to score them rather than report
something it could not defend.

## Round 3: auditing the audit

In October 2026 I re-read the negative result the way I had read the first fake positive.
Two numbers did not fit: the connectome's interval was **seven times wider** than the
nulls', and its per-seed scores were 0.67–0.82 on ten seeds and **0.21 and 0.20** — chance —
on seeds 5 and 9. Two seeds were carrying the whole negative.

I rebuilt the graph from the raw Janelia files on a fresh machine (identical totals) and
traced each failure.

**Seed 9 — "identical by construction" was not.** The harness matched each graph's gain
once, on seed 0's input pattern, with a comment saying drive statistics are identical across
seeds. But every seed stimulates a *different* random 10% of neurons. For a random graph that
hardly matters. For the connectome, whose activity runs through a few hubs, it is
everything: at one fixed gain its firing rate ranged from **0.01× to 1.97×** the target
across seeds. Seed 9 was effectively silent — 306 spikes against ~15,000 for the nulls —
and the liveness guard passed it because its threshold was one spike.

![rate spread](../figures/fig2_rate_spread.png)

**Seed 5 — the readout was looking at the wrong neurons.** Features came from 48 fixed
random "probe" neurons. On seed 5 the connectome fired 20,231 non-input spikes and **18**
landed on the probes. At a matched firing rate, the connectome's activity runs through about
33 of 450 neurons, a random graph's through about 70; 48 random probes catch about 4 of the
former. The positive control had in fact only passed with a 450-neuron readout — the powered
comparison then ran with 48, a configuration the control never validated.

![probe coverage](../figures/fig3_probe_coverage.png)

Both artifacts penalise a structured graph more than a random one, so the negative result
was not evidence about structure. It was also not evidence for it — seeds 0–11 had now been
looked at too closely to test anything on.

**So I preregistered the fix before running it.** [`EXP-E1-OP`](../experiments/results/EXP-E1-OP/protocol.md)
fixes the endpoint, the exclusion rules and 24 never-used seeds, and was pushed to GitHub
(commit `214c7c7`) before any of those seeds were simulated. It measures the full 2×2 —
gain matching {global, per-seed} × readout {48 probes, all non-input neurons} — for the
connectome, 20 degree-preserving and 20 random nulls, and a no-network baseline. The
original measurement is one cell of that grid and is unit-tested to be bit-identical to
the old harness.

<!-- RESULTS -->

## What I would tell a reviewer

- **The interesting skill here is not the simulator.** It is noticing that a result is too
  convenient — in either direction — and having the tooling to find out why in an afternoon:
  pinned data, versioned results, a slice small enough to ship in the repo, and tests that
  pin the old behaviour so the new one can be compared against it.
- **Negative results need audits too.** Round 2 was treated as the honest answer because it
  was unflattering. It had two artifacts in it, both biased against the hypothesis.
- **Preregistration is cheap.** A Markdown file and a commit timestamp turned a post-hoc
  rescue into a test that could have failed.

## Limits, stated plainly

- One task, one neuron model, one 500-neuron slice — the highest out-degree neurons, 0.3% of
  the CNS. It is mostly optic-lobe and central-brain interneurons; 243 of the 500 have no
  confidently predicted transmitter and are silenced (weight 0), 188 are inhibitory and 69
  excitatory, so this is an inhibition-dominated sub-network.
- Synapse count is used as weight; real synaptic strength, dynamics, gap junctions and
  neuromodulation are absent.
- The task is easy: a readout of the raw input with no network at all is competitive. The
  comparison is therefore between graphs as signal *carriers*, not between computers.
- Nothing here says anything about fly intelligence or biological computation.

## Repo pointers

| | |
|---|---|
| one-command tour on real data | `python -m flylab.demo` |
| preregistered 2×2 | [`experiments/results/EXP-E1-OP/protocol.md`](../experiments/results/EXP-E1-OP/protocol.md) |
| 2×2 runner | [`experiments/harness/e1_operating_point.py`](../experiments/harness/e1_operating_point.py) |
| nulls (and the bug history) | [`flylab/nulls.py`](../flylab/nulls.py) |
| first audit | [`reports/E1_audit_fixes.md`](../reports/E1_audit_fixes.md) |
| full experiment ledger | [`RESEARCH_LEDGER.yaml`](../RESEARCH_LEDGER.yaml) |
