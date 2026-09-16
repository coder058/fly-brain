#!/usr/bin/env python3
"""Read-only higher-order structure inventory for CIRCUIT-MINE-001."""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pyarrow.feather as feather
from scipy import sparse
from scipy.sparse import csgraph

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/derived/graph"
OUT = ROOT / "research/circuit_mining_summary.json"
REPORT_TOP_K = 20  # GUESS: descriptive review-list length; not a scientific threshold.
PERCENTILES = (0.0, 0.5, 0.9, 0.99, 1.0)  # SOURCE: standard descriptive breakpoints; not a gate.


def summary(values: np.ndarray) -> dict[str, float | int]:
    q = np.quantile(values, PERCENTILES)
    return {
        "min": float(q[0]),
        "median": float(q[1]),
        "p90": float(q[2]),
        "p99": float(q[3]),
        "max": float(q[4]),
        "mean": float(np.mean(values)),
    }


def top_counts(values: list[object], mask: np.ndarray, limit: int = REPORT_TOP_K) -> list[dict[str, object]]:
    counts = Counter(str(v) if v not in (None, "") else "UNANNOTATED" for v, keep in zip(values, mask) if keep)
    return [{"value": key, "count": int(count)} for key, count in counts.most_common(limit)]


def main() -> None:
    started = time.perf_counter()
    meta = json.loads((GRAPH / "graph_meta.json").read_text(encoding="utf-8"))
    n = int(meta["n_neurons"])
    expected_edges = int(meta["n_edges"])

    csr_npz = np.load(GRAPH / "csr_unsigned.npz", allow_pickle=False)
    csc_npz = np.load(GRAPH / "csc_unsigned.npz", allow_pickle=False)
    A = sparse.csr_matrix(
        (csr_npz["data"], csr_npz["indices"], csr_npz["indptr"]),
        shape=(n, n),
    )
    # A transpose in CSR form can reuse the existing CSC archive arrays.
    AT = sparse.csr_matrix(
        (csc_npz["data"], csc_npz["indices"], csc_npz["indptr"]),
        shape=(n, n),
    )
    out_degree = np.diff(A.indptr).astype(np.int64, copy=False)
    in_degree = np.diff(AT.indptr).astype(np.int64, copy=False)
    self_loops = int(A.diagonal().astype(bool).sum())

    reciprocal = A.multiply(AT)
    reciprocal_directed_edges = int(reciprocal.nnz)
    reciprocal_pairs = int((reciprocal_directed_edges - self_loops) // 2)
    reciprocal_degree = np.asarray(reciprocal.getnnz(axis=1)).ravel().astype(np.int64)
    strong_count, strong_labels = csgraph.connected_components(
        A, directed=True, connection="strong", return_labels=True
    )
    weak_count, weak_labels = csgraph.connected_components(
        A, directed=True, connection="weak", return_labels=True
    )
    strong_sizes = np.bincount(strong_labels)
    weak_sizes = np.bincount(weak_labels)
    largest_strong_label = int(np.argmax(strong_sizes))
    largest_strong_mask = strong_labels == largest_strong_label

    table = feather.read_table(
        GRAPH / "neurons.feather",
        columns=["neuron_id", "body_id", "type", "class", "superclass"],
    )
    ann = table.to_pydict()
    neuron_ids = np.asarray(ann["neuron_id"], dtype=np.int64)
    if not np.array_equal(neuron_ids, np.arange(n, dtype=np.int64)):
        raise ValueError("neurons.feather is not in node-id order; refusing ambiguous annotation join")
    top_nodes = np.argsort(-reciprocal_degree, kind="stable")[:REPORT_TOP_K]
    top_records = []
    for node in top_nodes:
        top_records.append({
            "node_id": int(node),
            "body_id": int(ann["body_id"][node]),
            "type": ann["type"][node],
            "class": ann["class"][node],
            "superclass": ann["superclass"][node],
            "in_degree": int(in_degree[node]),
            "out_degree": int(out_degree[node]),
            "reciprocal_degree": int(reciprocal_degree[node]),
        })

    result = {
        "analysis_id": "CIRCUIT-MINE-001",
        "status": "MEASURED_STRUCTURAL_INVENTORY",
        "read_only": True,
        "graph": {
            "n_neurons": n,
            "n_edges_metadata": expected_edges,
            "n_edges_csr": int(A.nnz),
            "self_loops": self_loops,
            "in_degree": summary(in_degree),
            "out_degree": summary(out_degree),
            "reciprocal_degree": summary(reciprocal_degree),
            "reciprocal_directed_edges": reciprocal_directed_edges,
            "reciprocal_pairs_excluding_self_loops": reciprocal_pairs,
            "reciprocal_edge_fraction_of_csr": reciprocal_directed_edges / expected_edges,
        },
        "components": {
            "strong_component_count": int(strong_count),
            "strongest_component_size": int(strong_sizes.max()),
            "strong_components_gt_one": int((strong_sizes > 1).sum()),
            "strong_component_top_sizes": [int(x) for x in np.sort(strong_sizes)[::-1][:REPORT_TOP_K]],
            "weak_component_count": int(weak_count),
            "weakest_component_count": int((weak_sizes == 1).sum()),
            "largest_weak_component_size": int(weak_sizes.max()),
        },
        "largest_strong_component_annotations": {
            "node_count": int(largest_strong_mask.sum()),
            "superclass": top_counts(ann["superclass"], largest_strong_mask),
            "class": top_counts(ann["class"], largest_strong_mask),
            "type": top_counts(ann["type"], largest_strong_mask),
        },
        "top_reciprocal_degree_nodes": top_records,
        "interpretation": {
            "measured": "Graph connectivity, reciprocity, degree distributions and annotation composition only.",
            "not_measured": "No task performance, memory, biological function, novelty or ML transfer.",
            "follow_up_rule": "A follow-up requires a mechanism-matched null, positive control, independent train/test data and valid seeded replication.",
        },
        "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "analysis_id": result["analysis_id"],
        "status": result["status"],
        "n_neurons": n,
        "n_edges": expected_edges,
        "strong_component_count": int(strong_count),
        "largest_strong_component": int(strong_sizes.max()),
        "reciprocal_directed_edges": reciprocal_directed_edges,
        "reciprocal_pairs": reciprocal_pairs,
        "runtime_seconds": result["runtime_seconds"],
        "output": str(OUT),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
