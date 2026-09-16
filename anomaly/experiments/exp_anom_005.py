#!/usr/bin/env python3
"""EXP-ANOM-005 — temporal hold-out: train on early normals, test later normals + anoms."""
from __future__ import annotations
import json
from run_common import run_exp

def main():
    results, path = run_exp(
        "EXP-ANOM-005",
        n_normal=240, n_anom=50, T=48, seed=5,
        anom_kind="local_glitch", noise=0.30, anom_strength=0.40, n_nodes=128,
        temporal_split=True, shuffle=False,
    )
    print(json.dumps({k: {"auroc": results["arms"][k]["auroc"], "auprc": results["arms"][k]["auprc"]} for k in results["arms"]}, indent=2))
    print("ceiling_like", results["ceiling_like"], "temporal_split", results["config"]["temporal_split"],
          "seconds", results["seconds"], "WROTE", path)

if __name__ == "__main__":
    main()
