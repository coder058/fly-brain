#!/usr/bin/env python3
"""Rebuild derived MaleCNS sparse graph from verified raw feathers.

Never writes to data/raw/. Default polarity policy is glutamate_unknown
(matches committed derived artifacts / graph_meta sign counts).

Usage:
  .venv/bin/python scripts/build_graph.py --out-dir /tmp/malecns_graph_check
  .venv/bin/python scripts/build_graph.py --policy glutamate_inhibitory --out-dir data/derived/graph_glu_inh
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.feather as feather
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/malecns_v1"
OUT_DEFAULT = ROOT / "data/derived/graph"
# GUESS: 500k rows bounds transient arrays; tune only from measured peak RSS.
EDGE_BATCH_ROWS = 500_000

# Inline policy table (same names as flylab.polarity.POLICIES) so this script
# stays runnable even if imports shift.
POLICIES = {
    "glutamate_unknown": {
        "excitatory": ["acetylcholine"],
        "inhibitory": ["gaba", "histamine"],
    },
    "glutamate_inhibitory": {
        "excitatory": ["acetylcholine"],
        "inhibitory": ["gaba", "histamine", "glutamate"],
    },
    "glutamate_excitatory": {
        "excitatory": ["acetylcholine", "glutamate"],
        "inhibitory": ["gaba", "histamine"],
    },
}


def pick_nt(gt, consensus) -> str:
    if gt is not None and str(gt).strip() and str(gt).lower() not in ("nan", "none"):
        return str(gt).strip().lower()
    if consensus is None or str(consensus).lower() in ("nan", "none"):
        return "unclear"
    return str(consensus).strip().lower()


def classify(nt: str, policy: str) -> int:
    spec = POLICIES[policy]
    if nt in {x.lower() for x in spec["excitatory"]}:
        return 1
    if nt in {x.lower() for x in spec["inhibitory"]}:
        return -1
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="glutamate_unknown", choices=sorted(POLICIES))
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="explicit side-directory; the protected derived graph is rejected")
    args = ap.parse_args()
    if args.out_dir is None:
        ap.error("--out-dir is required; refusing the protected data/derived/graph destination")
    out: Path = args.out_dir.resolve()
    protected = OUT_DEFAULT.resolve()
    if out == protected or protected in out.parents:
        ap.error(f"refusing to write inside protected graph directory: {protected}")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    ann = feather.read_table(RAW / "body-annotations-male-cns-v1.0-minconf-0.5.feather")
    traced_mask = pc.equal(ann["status"], "Traced")
    traced = ann.filter(traced_mask)
    body_sorted = np.sort(traced["bodyId"].combine_chunks().to_numpy().astype(np.int64))
    n = int(len(body_sorted))
    print(f"Traced {n}", flush=True)

    nt_tbl = feather.read_table(RAW / "body-neurotransmitters-male-cns-v1.0.feather")
    print("NT cols", nt_tbl.column_names, flush=True)
    nt_df = nt_tbl.to_pandas()
    sign_map: dict[int, int] = {}
    for body, gt, cons in zip(nt_df["body"], nt_df["ground_truth"], nt_df["consensus_nt"]):
        sign_map[int(body)] = classify(pick_nt(gt, cons), args.policy)

    signs = np.array([sign_map.get(int(b), 0) for b in body_sorted], dtype=np.int8)
    sc = {1: int((signs == 1).sum()), -1: int((signs == -1).sum()), 0: int((signs == 0).sum())}
    print("sign counts", sc, flush=True)

    edge_path = RAW / "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
    scanner = ds.dataset(edge_path, format="feather").scanner(
        columns=["body_pre", "body_post", "weight"],
        batch_size=EDGE_BATCH_ROWS,
        use_threads=False,
    )
    src_parts, dst_parts, weight_parts, sign_parts = [], [], [], []
    edges_scanned = 0
    weight_sum_exact = 0
    for batch in scanner.to_batches():
        pre = batch.column(0).to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
        post = batch.column(1).to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
        weights = batch.column(2).to_numpy(zero_copy_only=False)
        edges_scanned += len(pre)
        src_pos = np.searchsorted(body_sorted, pre)
        dst_pos = np.searchsorted(body_sorted, post)
        valid = (src_pos < n) & (dst_pos < n)
        valid &= body_sorted[np.minimum(src_pos, n - 1)] == pre
        valid &= body_sorted[np.minimum(dst_pos, n - 1)] == post
        src_batch = src_pos[valid].astype(np.int32, copy=False)
        dst_batch = dst_pos[valid].astype(np.int32, copy=False)
        selected_weights = weights[valid]
        weight_sum_exact += int(selected_weights.sum(dtype=np.int64))
        weight_batch = selected_weights.astype(np.float32, copy=False)
        src_parts.append(src_batch)
        dst_parts.append(dst_batch)
        weight_parts.append(weight_batch)
        sign_parts.append(signs[src_batch])
    src = np.concatenate(src_parts)
    dst = np.concatenate(dst_parts)
    w_f = np.concatenate(weight_parts)
    sign_pre = np.concatenate(sign_parts)
    del src_parts, dst_parts, weight_parts, sign_parts, scanner
    signed_w = w_f * sign_pre.astype(np.float32)

    print(f"edges scanned {edges_scanned} retained {len(w_f)} "
          f"weight_sum {weight_sum_exact}", flush=True)

    csr = sparse.coo_matrix((w_f, (src, dst)), shape=(n, n)).tocsr()
    csc = csr.tocsc()
    np.savez_compressed(
        out / "csr_unsigned.npz",
        data=csr.data,
        indices=csr.indices,
        indptr=csr.indptr,
        shape=np.array(csr.shape),
    )
    np.savez_compressed(
        out / "csc_unsigned.npz",
        data=csc.data,
        indices=csc.indices,
        indptr=csc.indptr,
        shape=np.array(csc.shape),
    )
    np.savez_compressed(
        out / "coo_signed.npz",
        src=src,
        dst=dst,
        weight=w_f,
        sign_pre=sign_pre,
        signed_weight=signed_w,
    )

    ann_df = feather.read_table(
        RAW / "body-annotations-male-cns-v1.0-minconf-0.5.feather"
    ).to_pandas()
    ann_df = ann_df[ann_df["status"] == "Traced"].copy()
    ann_df = ann_df.set_index("bodyId").loc[body_sorted].reset_index()
    ann_df = ann_df.rename(columns={"bodyId": "body_id"})
    ann_df["sign"] = signs
    ann_df["polarity_policy"] = args.policy
    feather.write_feather(ann_df, out / "neurons.feather")

    meta = {
        "filter": "status==Traced both ends",
        "polarity_policy": args.policy,
        "n_neurons": n,
        "n_edges": int(len(w_f)),
        "n_edges_csr_nnz": int(csr.nnz),
        "weight_sum": weight_sum_exact,
        "sign_counts": {"E": sc[1], "I": sc[-1], "U": sc[0]},
        "validation_targets": {
            "neurons": 166700,
            "edges": 25582938,
            "syn_contacts": 124000000,
        },
        "delta": {
            "neurons": n - 166700,
            "edges": int(len(w_f)) - 25582938,
            "weight_sum": weight_sum_exact - 124000000,
        },
        "seconds": round(time.time() - t0, 2),
        "artifacts": [
            "csr_unsigned.npz",
            "csc_unsigned.npz",
            "coo_signed.npz",
            "neurons.feather",
            "graph_meta.json",
        ],
    }
    (out / "graph_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("DONE", meta, flush=True)


if __name__ == "__main__":
    main()
