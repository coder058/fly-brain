# MOTIF-FUNC-003 through 006 control construction erratum

The archived full runs and audits under `research/results/MOTIF-FUNC-003/`
through `research/results/MOTIF-FUNC-006/` used runner revision
`2ddf9b49748e`.
Their source and destination edge endpoints are **local** indices into a
selected subgraph. The runners indexed the **global** superclass array with
those local indices when forming permutation blocks. This is a construction
error in the intended source-superclass to destination-superclass controls.

The archived numerical contrasts remain available for provenance, but their
block-preserving interpretation and any downstream claim based on them are
**invalid**. This includes the formerly positive MOTIF-FUNC-003 comparison.
The old audits checked invariants against the same incorrectly formed blocks;
a passing audit does not repair the label mapping.

A read-only audit on Frankfurt using the protected derived graph found **21,921
different block assignments among 23,704 analyzed edge records**. The archived
implementation formed 71 block keys; the intended local-to-global mapping
forms 40. These are measured with
`python scripts/audit_motif_block_labels.py` against the verified MaleCNS
derived graph. `scripts/verify_graph.py` passed, and SHA-256 checks of the four
graph archives matched before and after the audit. This counts assignment
differences, not a corrected routing-margin result.

The corrected runners map `labels[selected_nodes]` before constructing blocks,
retain isolated selected nodes in the matrix shape, and reject mismatched or
out-of-range inputs. Synthetic regression tests cover nonconsecutive global
IDs and block invariants. A new experiment needs its own runner hash and
read-only graph provenance; it must not overwrite the archived runs. Because
the earlier results were seen, a corrected rerun is a disclosed repair, not
an untouched confirmatory test.

This erratum is about functional controls, not a memory curve. EXP-MEM-003
remains `MEM_003_NO_PAIR`, with no valid paired memory curve.

## Corrected Frankfurt reruns, 27 September 2026

Each repaired control completed smoke, a one-seed operational sizing check,
and a full 12-seed run on the Frankfurt VPS. The new audit recomputed block
invariants using the actual selected global node IDs, checked the paired
arithmetic and train/test liveness, and matched runner and protocol hashes.
The protected graph archives retained their SHA-256 hashes. Each audit reports
`AUDIT_PASSED_ENGINEERING_ONLY`.

| Control | Measured pairs | Observed minus control margin | 95% paired t interval | Registered gate on repaired run |
| --- | ---: | ---: | --- | --- |
| [003 weight](../research/results/MOTIF-FUNC-003/FULL_20260927T132656Z_72ba11b467c0/summary.json) | 12 | +0.067708 | [+0.014723, +0.120693] | Positive direction under the fixed readout; post-result repair |
| [004 sign](../research/results/MOTIF-FUNC-004/FULL_20260927T132811Z_72ba11b467c0/summary.json) | 6 | +0.097222 | [-0.026969, +0.221414] | Inconclusive; fewer than eight pairs |
| [005 magnitude](../research/results/MOTIF-FUNC-005/FULL_20260927T132905Z_72ba11b467c0/summary.json) | 10 | -0.100000 | [-0.176896, -0.023104] | Control above observed under the fixed readout; post-result repair |
| [006 lower target](../research/results/MOTIF-FUNC-006/FULL_20260927T133001Z_72ba11b467c0/summary.json) | 11 | -0.081439 | [-0.183994, +0.021115] | Inconclusive; interval crosses zero |

All values above are rounded displays of the linked JSON, not new estimates.
The [003 audit](../research/results/MOTIF-FUNC-003/AUDIT_REPAIR_20260927T133329Z_9b1665d0e421/summary.json),
[004 audit](../research/results/MOTIF-FUNC-004/AUDIT_REPAIR_20260927T133335Z_9b1665d0e421/summary.json),
[005 audit](../research/results/MOTIF-FUNC-005/AUDIT_REPAIR_20260927T133341Z_9b1665d0e421/summary.json), and
[006 audit](../research/results/MOTIF-FUNC-006/AUDIT_REPAIR_20260927T133347Z_9b1665d0e421/summary.json)
provide the checks. The full runs do **not** turn the archival results into
independent confirmations: the earlier outcomes were known before the repair.
Neither a functional readout difference nor paper-style repeated compute
establishes biological memory or a connectome advantage.
