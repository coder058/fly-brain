# EXP-E2-HD — report

Protocol: [`experiments/results/EXP-E2-HD/protocol.md`](../experiments/results/EXP-E2-HD/protocol.md),
pushed as `4bd743c` (2026-10-23 00:11:47 UTC); the run started at 00:11:56 UTC.
Artifact: `experiments/results/EXP-E2-HD/hd_confirmatory_20261023T001156Z_4bd743c.json`.

## Outcome

**Primary (delay 5): connectome − topography null = +0.143, 95% CI [+0.135, +0.151]**, n = 24,
**24 of 24 seeds** in favour. Under the preregistered rule: *the head-direction map carries
position better than the same circuit with its map shuffled.*

Calibration passed: `no_network` produced no measurement at any delay (with no recurrent
connections the pool is silent after the pulse, so there is no path from input to readout).

| delay (steps after pulse) | connectome | Dale degree null | topography null | conn − Dale null | conn − topography null |
|---|---|---|---|---|---|
| **5** | **0.984** | 0.844 | 0.841 | +0.140 [+0.131, +0.149] (24/24) | **+0.143 [+0.135, +0.151] (24/24)** |
| 15 | 0.322 | 0.267 | 0.231 | +0.055 [+0.037, +0.073] (21/24) | +0.091 [+0.073, +0.108] (24/24) |
| 30 | 0.224 | 0.218 | 0.229 | +0.005 [−0.017, +0.027] | −0.006 [−0.027, +0.015] |
| 60 | 0.231 | 0.209 | 0.231 | +0.022 [+0.003, +0.041] | −0.000 [−0.016, +0.016] |

Chance is 0.125. Null values are means over 10 draws per seed.

## Reading

1. **The map matters for carrying a spatial signal.** Keeping every neuron's degrees, its
   outgoing weights and sign, *and* every cell-type-to-cell-type edge count, but shuffling
   which neuron within a type connects to which, drops position decoding five steps after the
   pulse from 0.98 to 0.84. The readout is retrained for every graph, so a fixed random
   mapping would still be decodable in principle; what the real map adds is convergence —
   neurons tuned to the same position project onto shared targets, so their signals sum.
2. **Not a memory result.** By 30 steps all wirings sit at ≈ 0.22, above chance but equal.
   Under this LIF model the circuit is bistable (silent or near-saturated after the pulse), so
   it never forms the persistent "bump" a ring attractor would hold. That is a limitation of
   the neuron model, stated in the protocol before the run, not evidence about the fly.
3. **The instrument can see wiring effects.** The same pipeline that returned "not supported"
   for the degree-ranked slices of E1 detects a large, unanimous effect in a circuit whose
   anatomy predicts one. That makes the E1 negative more informative: it is not simply an
   instrument that cannot detect structure.

## Robustness (post hoc, not preregistered)

Every topography-null cell in the confirmatory run selected the same grid gain (6.0), which
raised the possibility that the 12-value grid was too coarse around the null's operating
point while covering the connectome's (2–4) densely. A rerun on seeds 6000–6007 with a
45-value grid (1.00 to 12.00 in steps of 0.25), delays 5 and 15:
`experiments/results/EXP-E2-HD/hd_robustness-finegrid_20261023T002832Z_b61d961.json`.

| delay | connectome | Dale null | topography null | conn − topography |
|---|---|---|---|---|
| 5 | 0.982 | 0.846 | 0.827 | +0.155 [+0.139, +0.171] (n = 8) |
| 15 | 0.326 | 0.264 | 0.229 | +0.096 [+0.055, +0.137] (n = 8) |

With the fine grid the topography null chose gains 5.5–7.0 and did not improve; the effect
is unchanged. The grid was not the explanation.

## Exploratory pilot (before the protocol)

Dev seeds 0–1 were used to choose the design: a gain sweep showed the bistability that rules
out rate matching, and short-delay decoding already favoured the connectome (0.99 vs
0.76–0.79). Those seeds are not part of any result above.

## Limits

- One circuit, one task, one simple neuron model; the effect is about transmission one to two
  synapses downstream, which the anatomy predicts. It is a sensitivity check, not a discovery.
- Synapse counts as weights; no PEN-mediated angular-velocity input, no visual input, no
  short-term synaptic dynamics.
- Only right-PB EPGs are stimulated; the readout excludes them by construction.
