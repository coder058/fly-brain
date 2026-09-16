# Frozen graph integrity — 2026-09-16

`scripts/verify_graph.py` performed a read-only check of
`data/derived/graph/`; it did not read `data/raw/` and did not run
`scripts/build_graph.py`.

Result: `PASS_STRUCTURAL_CHECKS`.

- Metadata: 165122 neurons, 25563197 edges, `n_edges_csr_nnz` 25563197.
- CSR, CSC, and COO archives all contain 25563197 entries and have the
  metadata-sized graph bounds.
- CSR and CSC contain no explicit zero values.
- COO signs are restricted to `-1, 0, 1`; `signed_weight == weight * sign_pre`
  for every stored edge.
- The metadata `weight_sum` is 124025046; the verifier reports the float32
  archive sum separately and does not reinterpret it as a new finding.

SHA-256 of the current read-only inputs:

| File | SHA-256 |
|---|---|
| `csr_unsigned.npz` | `b6dbd38b2c7a2771ac61d04c84add24733164cbbd26872bd417a02de7afd7949` |
| `csc_unsigned.npz` | `1db82dc9ea509c4e14f173bcfbcbf8170830839718aee373e1ee609441d6aa4f` |
| `coo_signed.npz` | `88289920f5ad069b8592168f9f9292dad49af8c6e29633ee8ad1e6176f2eccf5` |
| `graph_meta.json` | `7a50f8de7a67793253f498b69b595e3310b1bf5abc876a929c69a0bbe3704fb1` |
