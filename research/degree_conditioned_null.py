#!/usr/bin/env python3
"""Read-only degree-conditioned label null for CIRCUIT-MINE-003."""
from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.feather as feather
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/derived/graph"
OUT = ROOT / "research/degree_conditioned_null_summary.json"
N_PERMUTATIONS = 20  # SOURCE: preregistered in CIRCUIT-MINE-003 protocol.
RNG_SEED = 0  # SOURCE: fixed preregistered null stream.


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
    AT = sparse.csr_matrix(
        (csc_npz["data"], csc_npz["indices"], csc_npz["indptr"]),
        shape=(n, n),
    )
    out_degree = np.diff(A.indptr).astype(np.int64, copy=False)
    in_degree = np.diff(AT.indptr).astype(np.int64, copy=False)

    edge_npz = np.load(GRAPH / "coo_signed.npz", allow_pickle=False)
    src = edge_npz["src"].astype(np.int64, copy=False)
    dst = edge_npz["dst"].astype(np.int64, copy=False)
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
    label_values = np.asarray(
        [str(x) if x not in (None, "") else "UNANNOTATED" for x in ann["superclass"]],
        dtype=str,
    )
    names, labels = np.unique(label_values, return_inverse=True)
    src_labels = labels[src]
    dst_labels = labels[dst]
    observed_same = float(np.mean(src_labels == dst_labels))

    degree_pairs = np.column_stack((in_degree, out_degree))
    _, strata = np.unique(degree_pairs, axis=0, return_inverse=True)
    members = defaultdict(list)
    for node, stratum in enumerate(strata):
        members[int(stratum)].append(node)
    strata_indices = [np.asarray(nodes, dtype=np.int64) for nodes in members.values()]

    rng = np.random.default_rng(RNG_SEED)
    null_fractions = []
    for _ in range(N_PERMUTATIONS):
        permuted = labels.copy()
        for indices in strata_indices:
            if len(indices) > 1:
                permuted[indices] = labels[rng.permutation(indices)]
        null_fractions.append(float(np.mean(permuted[src] == permuted[dst])))
    null_array = np.asarray(null_fractions, dtype=np.float64)

    group_reports = []
    for code, name in enumerate(names):
        source_mask = src_labels == code
        internal_mask = source_mask & (dst_labels == code)
        source_edges = int(source_mask.sum())
        internal_edges = int(internal_mask.sum())
        group_reports.append({
            "superclass": str(name),
            "nodes": int((labels == code).sum()),
            "source_edges": source_edges,
            "observed_internal_edges": internal_edges,
            "observed_internal_fraction": (
                internal_edges / source_edges if source_edges else None
            ),
        })

    result = {
        "analysis_id": "CIRCUIT-MINE-003",
        "status": "MEASURED_DEGREE_CONDITIONED_NULL",
        "read_only": True,
        "graph": {"n_neurons": n, "n_edges": expected_edges},
        "strata": {
            "definition": "exact (in_degree, out_degree) pair",
            "count": int(len(strata_indices)),
            "label_permutations_within_strata": N_PERMUTATIONS,
        },
        "annotation_alignment": {
            "label_field": "superclass",
            "observed_same_superclass_edge_fraction": observed_same,
            "null_fractions": null_fractions,
            "null_mean": float(null_array.mean()),
            "null_sd": float(null_array.std(ddof=1)),
            "delta_observed_minus_null_mean": float(observed_same - null_array.mean()),
        },
        "groups": group_reports,
        "interpretation": {
            "measured": "Superclass-label alignment after preserving exact node degree pairs and label counts.",
            "not_measured": "No biological function, task performance, routing benefit, memory or ML transfer.",
            "decision": "PENDING_PRIOR_ART_AND_TASK_DESIGN",
        },
        "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "analysis_id": result["analysis_id"],
        "status": result["status"],
        "observed": observed_same,
        "null_mean": float(null_array.mean()),
        "null_sd": float(null_array.std(ddof=1)),
        "delta": float(observed_same - null_array.mean()),
        "degree_pair_strata": int(len(strata_indices)),
        "runtime_seconds": result["runtime_seconds"],
        "output": str(OUT),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
