#!/usr/bin/env python3
"""Read-only structural and checksum verification for the frozen graph."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_sparse_archive(path: Path, n: int, expected_edges: int):
    with np.load(path, allow_pickle=False) as archive:
        required = {"data", "indices", "indptr", "shape"}
        if set(archive.files) != required:
            raise ValueError(f"{path.name}: keys {archive.files} != {sorted(required)}")
        shape = tuple(int(x) for x in archive["shape"])
        data = archive["data"]
        indices = archive["indices"]
        indptr = archive["indptr"]
        if shape != (n, n):
            raise ValueError(f"{path.name}: shape {shape} != {(n, n)}")
        if len(data) != expected_edges or len(indices) != expected_edges:
            raise ValueError(f"{path.name}: edge arrays do not match metadata")
        if len(indptr) != n + 1:
            raise ValueError(f"{path.name}: indptr length is not n+1")
        if len(indices) and (int(indices.min()) < 0 or int(indices.max()) >= n):
            raise ValueError(f"{path.name}: index outside graph bounds")
        return {
            "shape": list(shape),
            "nnz": int(len(data)),
            "explicit_zero_values": int(np.count_nonzero(data == 0)),
            "data_dtype": str(data.dtype),
            "indices_dtype": str(indices.dtype),
        }


def check_coo(path: Path, n: int, expected_edges: int):
    with np.load(path, allow_pickle=False) as archive:
        required = {"src", "dst", "weight", "sign_pre", "signed_weight"}
        if set(archive.files) != required:
            raise ValueError(f"{path.name}: keys {archive.files} != {sorted(required)}")
        src, dst = archive["src"], archive["dst"]
        weight, sign_pre, signed_weight = (
            archive["weight"], archive["sign_pre"], archive["signed_weight"]
        )
        if any(len(x) != expected_edges for x in (src, dst, weight, sign_pre, signed_weight)):
            raise ValueError(f"{path.name}: arrays do not match metadata edge count")
        for name, values in (("src", src), ("dst", dst)):
            if len(values) and (int(values.min()) < 0 or int(values.max()) >= n):
                raise ValueError(f"{path.name}: {name} outside graph bounds")
        unique_signs = set(int(x) for x in np.unique(sign_pre))
        if not unique_signs.issubset({-1, 0, 1}):
            raise ValueError(f"{path.name}: unexpected sign values {unique_signs}")
        if not np.array_equal(signed_weight, weight * sign_pre):
            raise ValueError(f"{path.name}: signed_weight != weight * sign_pre")
        return {
            "edges": int(len(weight)),
            "edge_sign_counts": {str(int(k)): int(v) for k, v in
                                  zip(*np.unique(sign_pre, return_counts=True))},
            "signed_weight_explicit_zeros": int(np.count_nonzero(signed_weight == 0)),
            "weight_sum_float64_of_float32": float(np.asarray(weight, dtype=np.float64).sum()),
            "signed_weight_sum_float64_of_float32": float(np.asarray(signed_weight, dtype=np.float64).sum()),
            "weight_dtype": str(weight.dtype),
        }


def verify(graph_dir: Path) -> dict:
    meta_path = graph_dir / "graph_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    n = int(meta["n_neurons"])
    expected_edges = int(meta["n_edges"])
    files = {
        name: graph_dir / name
        for name in ("csr_unsigned.npz", "csc_unsigned.npz", "coo_signed.npz", "graph_meta.json")
    }
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(missing)
    csr = check_sparse_archive(files["csr_unsigned.npz"], n, expected_edges)
    csc = check_sparse_archive(files["csc_unsigned.npz"], n, expected_edges)
    coo = check_coo(files["coo_signed.npz"], n, expected_edges)
    checks = {
        "metadata_n_neurons": n,
        "metadata_n_edges": expected_edges,
        "metadata_n_edges_csr_nnz": int(meta["n_edges_csr_nnz"]),
        "csr_matches_metadata": csr["nnz"] == int(meta["n_edges_csr_nnz"]),
        "csc_matches_metadata": csc["nnz"] == expected_edges,
        "coo_matches_metadata": coo["edges"] == expected_edges,
        "all_sparse_archives_have_no_explicit_zero_values": (
            csr["explicit_zero_values"] == 0 and csc["explicit_zero_values"] == 0
        ),
        "signed_weight_identity": True,
    }
    return {
        "status": "PASS_STRUCTURAL_CHECKS" if all(checks.values()) else "FAIL",
        "graph_dir": str(graph_dir),
        "metadata": meta,
        "files_sha256": {name: sha256(path) for name, path in files.items()},
        "csr": csr,
        "csc": csc,
        "coo": coo,
        "checks": checks,
        "weight_sum_note": "metadata weight_sum is exact pre-float32 conversion; float32 archive sum is reported separately",
        "read_only": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-dir", type=Path, default=Path("data/derived/graph"))
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.graph_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
