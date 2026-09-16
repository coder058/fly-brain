# `ops_proxy` accounting audit — 2026-09-16

The E1 reservoir runner now computes its operation proxy from executable
nonzero sparse synapses, not from `W.nnz` when `W` contains explicit zeros.
Each arm records both `stored_nnz` and `effective_nnz`; the proxy uses the
latter. The helper also handles dense arrays without changing their count.

The regression test constructs a sparse matrix with one explicit zero and
verifies that only the two nonzero entries contribute to the proxy. Targeted
controls/liveness tests pass `13/13`; the full suite must remain the final
gate. This is an accounting correction, not a performance or topology result.
