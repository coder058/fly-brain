# MaleCNS derived-graph rebuild audit — 2026-09-16

**Result:** the rebuilt CSR, CSC and signed COO arrays are byte-identical to the existing graph. The original `data/derived/graph/` and every `data/raw/` file remained untouched.

## Verified values

| Check | Existing | Rebuilt | Result |
|---|---:|---:|---|
| Neurons | 165,122 | 165,122 | equal |
| Directed edges / CSR nnz | 25,563,197 | 25,563,197 | equal |
| Exact weight sum | 124,025,046 | 124,025,046 | equal |
| Sign counts E/I/U | 103,718 / 27,965 / 33,439 | same | equal |
| CSR SHA-256 | `b6dbd38b2c7a2771ac61d04c84add24733164cbbd26872bd417a02de7afd7949` | same | byte-identical |
| CSC SHA-256 | `1db82dc9ea509c4e14f173bcfbcbf8170830839718aee373e1ee609441d6aa4f` | same | byte-identical |
| Signed COO SHA-256 | `88289920f5ad069b8592168f9f9292dad49af8c6e29633ee8ad1e6176f2eccf5` | same | byte-identical |
| `neurons.feather` | 5,386,554 bytes | 14,684,578 bytes | schema differs; `body_id` and `sign` arrays equal |

Existing `graph_meta.json` SHA-256 after the run: `7a50f8de7a67793253f498b69b595e3310b1bf5abc876a929c69a0bbe3704fb1`. Its rebuild metadata has the same scientific fields; elapsed `seconds` is inherently run-specific, so the JSON files are not byte-compared.

All three raw-file hashes were rechecked against `data/manifests/source.lock.json` after the run and match. No writes targeted `data/raw/` or the existing derived graph.

## Memory failure and repair

The initial builder OOM-killed a process at 15,591,808 KiB RSS because Feather contained 151,856,684 raw rows before filtering and the script materialized every column plus full-size membership temporaries. A capped retry identified a second allocation: NumPy `isin` attempted a 1.13 GiB temporary for a 151,856,684-element column. Both failed runs wrote only to empty temporary output directories; neither changed the source graph.

`scripts/build_graph.py` now selects only `body_pre`, `body_post`, and `weight`, streams 500,000-row batches, filters against sorted traced IDs, and accumulates integer weight sums before converting edge weights to float32. A successful isolated rebuild to `/tmp/fly-lab-graph-repro-final-g8nfusrz` took 88.87 s and peaked at 2,256,780 KiB RSS under a 10 GiB process virtual-memory cap. Its core sparse artifacts matched exactly.

The rebuilt neuron Feather keeps the complete raw annotation projection; the current derived file is narrower. Since the fields consumed downstream (`body_id`, `sign`) are equal, this is a packaging/schema difference, not a graph discrepancy. If byte-identical neuron metadata is required later, freeze the desired column projection explicitly.
