#!/usr/bin/env python3
"""EXP-ANOM-004 — same subtle glitch as 002, increasing observation noise."""
from __future__ import annotations
import json
from run_common import run_exp

def main():
    sweep = []
    for noise in (0.15, 0.35, 0.55, 0.80):
        results, path = run_exp(
            "EXP-ANOM-004",
            n_normal=180, n_anom=45, T=48, seed=4,
            anom_kind="local_glitch", noise=noise, anom_strength=0.35, n_nodes=128,
        )
        row = {
            "noise": noise,
            "path": str(path),
            "seconds": results["seconds"],
            "auroc": {k: results["arms"][k]["auroc"] for k in results["arms"]},
        }
        sweep.append(row)
        print(f"noise={noise} auroc={json.dumps(row['auroc'])} s={results['seconds']}", flush=True)
    summary = {"exp": "EXP-ANOM-004", "sweep": sweep, "claim_ready": False}
    out = path.parent / "exp_anom_004_sweep.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print("WROTE", out)

if __name__ == "__main__":
    main()
