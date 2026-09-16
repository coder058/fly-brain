#!/usr/bin/env python3
"""EXP-ANOM-002 — subtle anomalies (lower strength + drift/glitch)."""
from __future__ import annotations
import json
from run_common import run_exp

def main():
    # Mix of subtle kinds across one report: primary = local_glitch @ low strength
    results, path = run_exp(
        "EXP-ANOM-002",
        n_normal=200, n_anom=50, T=48, seed=1,
        anom_kind="local_glitch", noise=0.25, anom_strength=0.35, n_nodes=128,
    )
    print(json.dumps({k: {"auroc": results["arms"][k]["auroc"]} for k in results["arms"]}, indent=2))
    print("ceiling_like", results["ceiling_like"], "seconds", results["seconds"], "WROTE", path)

if __name__ == "__main__":
    main()
