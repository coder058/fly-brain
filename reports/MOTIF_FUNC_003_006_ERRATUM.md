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
