# Prior art — Fly Lab

This review uses primary literature only. It constrains novelty claims; it does
not imply that the current repository reproduces any cited result.

| Hypothesis / observation | Closest primary work | What is known | What remains missing here | What Fly Lab should test | Why it might differ |
|---|---|---|---|---|---|
| CIRCUIT-MINE-001: giant SCC / recurrence | [Network statistics of the whole-brain connectome of Drosophila](https://www.nature.com/articles/s41586-024-07968-y) | Whole-brain fly connectome analyses already report a giant strongly connected component, reciprocity, motifs, rich-club structure, and neuropil-scale organization. | Our graph/filter is MaleCNS v1.0 and the analysis is a repository validation; no new biological or computational function follows. | Do not spend budget on generic recurrence. Test a specific mechanism at a controlled task level. | Different graph version/filter can be a reproducibility comparison, not novelty by itself. |
| CIRCUIT-MINE-002/003: annotation-conditioned blocks | [Network statistics of the whole-brain connectome of Drosophila](https://www.nature.com/articles/s41586-024-07968-y); [Distributed control circuits across a brain-and-cord connectome](https://www.nature.com/articles/s41586-026-10735-w) | Region/neuropil organization, modular structure, local feedback, and long-range distributed circuits are established topics. | Our result is only superclass edge alignment; it lacks spatial/neuropil controls, sign/weight/motif analysis, and task behavior. | Test whether the observed blocks implement conditional routing or interference control under matched compute and strong nulls. | The unit of analysis and task could differ, but novelty is UNVERIFIED until compared and replicated. |
| Connectome-constrained computation | [Connectome-constrained networks predict neural activity across the fly visual system](https://www.nature.com/articles/s41586-024-07939-3) | Recurrent connectome-constrained networks with cell-type parameter sharing have been trained to predict visual-system activity and temporal integration. | Fly Lab has not shown a task result or a minimal abstraction from its blocks; generic “connectome helps ML” would be an inadequate claim. | Compare a minimal block-conditioned routing operator against matched sparse/dense baselines on a preregistered two-stream task. | The proposed operator would target routing/interference, not visual activity prediction; novelty remains unverified. |
| Recurrent learning / Mushroom Body | [Recurrent architecture for adaptive regulation of learning in the insect brain](https://www.nature.com/articles/s41593-020-0607-9) | A synaptic-resolution MB circuit and feedback motifs have been modeled for adaptive learning. | Earlier memory results here were instrument-limited/invalidated; no claim about MB memory is warranted. | Do not reopen MB by default; test the surviving routing mechanism first. | A different circuit/task would be a new question, not a claim that MB literature was absent. |
| Recurrent sensory computation | [Recurrent circuitry shapes hue selectivity in Drosophila](https://www.nature.com/articles/s41593-024-01640-4) | Recurrent circuitry can contribute to a specific sensory computation. | No comparable sensory task or circuit-specific ablation has been run here. | Use mechanism-matched functional tasks, not generic reservoir scores. | Potentially relevant only if the mined circuit is tied to a comparable computation. |

## Literature decision

CIRCUIT-MINE-001/002/003 are structural observations, not breakthroughs.
The closest work makes giant recurrence and anatomical organization expected rather
than novel. The highest-value surviving direction is a falsifiable,
annotation-conditioned routing/interference task with degree- and
module-aware controls. Any ML abstraction must wait for a positive-control
calibrated task effect, replication, and adversarial review.
