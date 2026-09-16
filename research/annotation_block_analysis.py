#!/usr/bin/env python3
"""Read-only annotation-conditioned block analysis for CIRCUIT-MINE-002."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pyarrow.feather as feather
from scipy import sparse
from scipy.sparse import csgraph

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/derived/graph"
OUT = ROOT / "research/annotation_block_summary.json"
N_PERMUTATIONS = 20  # SOURCE: preregistered in CIRCUIT-MINE-002 protocol.
MIN_GROUP_NODES = 100  # GUESS: descriptive stability cutoff; not a scientific gate.


def main() -> None:
    started = time.perf_counter()
    meta = json.loads((GRAPH / "graph_meta.json").read_text(encoding="utf-8"))
    n = int(meta["n_neurons"])
    expected_edges = int(meta["n_edges"])

    csr_npz = np.load(GRAPH / "csr_unsigned.npz", allow_pickle=False)
    A = sparse.csr_matrix(
        (csr_npz["data"], csr_npz["indices"], csr_npz["indptr"]),
        shape=(n, n),
    )
    coo_npz = np.load(GRAPH / "coo_signed.npz", allow_pickle=False)
    src = coo_npz["src"].astype(np.int64, copy=False)
    dst = coo_npz["dst"].astype(np.int64, copy=False)
    if len(src) != expected_edges or len(dst) != expected_edges:
        raise ValueError("COO edge count does not match metadata")

    table = feather.read_table(
        GRAPH / "neurons.feather",
        columns=["neuron_id", "superclass"],
    )
    ann = table.to_pydict()
    node_ids = np.asarray(ann["neuron_id"], dtype=np.int64)
    if not np.array_equal(node_ids, np.arange(n, dtype=np.int64)):
        raise ValueError("neurons.feather is not in node-id order")
    labels = np.asarray(
        [str(x) if x not in (None, "") else "UNANNOTATED" for x in ann["superclass"]],
        dtype=str,
    )
    names, node_codes = np.unique(labels, return_inverse=True)
    src_codes = node_codes[src]
    dst_codes = node_codes[dst]
    same_observed = float(np.mean(src_codes == dst_codes))

    group_reports = []
    for code, name in enumerate(names):
        node_mask = node_codes == code
        source_edge_mask = src_codes == code
        internal_edge_mask = source_edge_mask & (dst_codes == code)
        internal_edges = int(internal_edge_mask.sum())
        source_edges = int(source_edge_mask.sum())
        sub = A[node_mask][:, node_mask]
        scc_count, scc_labels = csgraph.connected_components(
            sub, directed=True, connection="strong", return_labels=True
        )
        scc_sizes = np.bincount(scc_labels) if len(scc_labels) else np.array([0])
        group_reports.append({
            "superclass": str(name),
            "nodes": int(node_mask.sum()),
            "source_edges": source_edges,
            "internal_edges": internal_edges,
            "internal_fraction_of_source_edges": (
                internal_edges / source_edges if source_edges else None
            ),
            "strong_component_count": int(scc_count),
            "largest_strong_component": int(scc_sizes.max()),
            "included_in_stable_scc_report": bool(node_mask.sum() >= MIN_GROUP_NODES),
        })

    rng = np.random.default_rng(0)  # SOURCE: fixed preregistered null stream.
    null_fractions = []
    for _ in range(N_PERMUTATIONS):
        permuted_codes = node_codes[rng.permutation(n)]
        null_fractions.append(float(np.mean(permuted_codes[src] == permuted_codes[dst])))
    null_array = np.asarray(null_fractions, dtype=np.float64)

    result = {
        "analysis_id": "CIRCUIT-MINE-002",
        "status": "MEASURED_STRUCTURAL_BLOCK_ANALYSIS",
        "read_only": True,
        "graph": {
            "n_neurons": n,
            "n_edges": expected_edges,
            "superclass_count": int(len(names)),
        },
        "annotation_alignment": {
            "label_field": "superclass",
            "observed_same_superclass_edge_fraction": same_observed,
            "permutation_null": {
                "n": N_PERMUTATIONS,
                "fractions": null_fractions,
                "mean": float(null_array.mean()),
                "sd": float(null_array.std(ddof=1)),
                "delta_observed_minus_null_mean": float(same_observed - null_array.mean()),
            },
        },
        "groups": group_reports,
        "interpretation": {
            "measured": "Superclass-label alignment with graph edges and within-group connectivity.",
            "not_measured": "No biological function, task performance, memory, routing benefit, novelty or ML transfer.",
            "decision": "PENDING_ADVERSARIAL_REVIEW",
        },
        "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "analysis_id": result["analysis_id"],
        "status": result["status"],
        "observed_same_superclass_edge_fraction": same_observed,
        "null_mean": float(null_array.mean()),
        "null_sd": float(null_array.std(ddof=1)),
        "delta_observed_minus_null_mean": float(same_observed - null_array.mean()),
        "groups": int(len(names)),
        "runtime_seconds": result["runtime_seconds"],
        "output": str(OUT),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
