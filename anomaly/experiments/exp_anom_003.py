#!/usr/bin/env python3
"""EXP-ANOM-003 — rare anomalies (~5% prevalence)."""
from __future__ import annotations
import json
from run_common import run_exp

def main():
    results, path = run_exp(
        "EXP-ANOM-003",
        n_normal=400, n_anom=20, T=48, seed=2,
        anom_kind="drift", noise=0.2, anom_strength=0.5, n_nodes=128,
    )
    print(json.dumps({k: {"auroc": results["arms"][k]["auroc"], "auprc": results["arms"][k]["auprc"]} for k in results["arms"]}, indent=2))
    print("ceiling_like", results["ceiling_like"], "prevalence", results["config"]["prevalence"],
          "seconds", results["seconds"], "WROTE", path)

if __name__ == "__main__":
    main()
