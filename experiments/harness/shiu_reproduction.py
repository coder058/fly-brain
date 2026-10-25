"""Reproduce Shiu et al.'s published FlyWire sugar simulations with flylab.brain.

Reference: the authors' own Brian 2 outputs shipped in their repository
(`results/example/sugarR.parquet`, 200 Hz; `sugarR_100Hz.parquet`, 100 Hz): spike times of
every neuron over 30 one-second trials with the 21 right-hemisphere sugar GRNs activated.
We run the same conditions on the same FlyWire 630 table and compare per-neuron rates.
Poisson draws differ between simulators, so agreement is statistical, not spike-exact
(spike-exact equivalence with Brian 2 is covered by tests/test_brain.py).
"""
from __future__ import annotations

import os

for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "harness"))

import e1_reservoir as H  # noqa: E402  (provenance helpers)
from flylab.brain import BrainModel, run_trials  # noqa: E402
from flylab.connectomes import SHIU_DIR, load_flywire_630  # noqa: E402

SUGAR_R = [  # Shiu et al. example.ipynb / figures.ipynb, verbatim
    720575940624963786, 720575940630233916, 720575940637568838, 720575940638202345,
    720575940617000768, 720575940630797113, 720575940632889389, 720575940621754367,
    720575940621502051, 720575940640649691, 720575940639332736, 720575940616885538,
    720575940639198653, 720575940620900446, 720575940617937543, 720575940632425919,
    720575940633143833, 720575940612670570, 720575940628853239, 720575940629176663,
    720575940611875570,
]
MN9_FLYWIRE = 720575940660219265
REFERENCES = {200.0: "sugarR.parquet", 100.0: "sugarR_100Hz.parquet"}


def reference_rates(path: Path) -> dict[int, float]:
    import pandas as pd

    d = pd.read_parquet(path, columns=["trial", "flywire_id"])
    n_trials = d["trial"].nunique()
    return (d.groupby("flywire_id").size() / n_trials).astype(float).to_dict()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=2024)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "experiments/results/SHIU-REPRO")
    args = ap.parse_args(argv)
    started = {**H.provenance(),
               "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]}
    c = load_flywire_630()
    model = BrainModel(c.W)
    exc = c.index_of(SUGAR_R)
    mn9 = int(c.index_of([MN9_FLYWIRE])[0])
    out = {"experiment": "SHIU-REPRO", "provenance": started, "connectome": c.meta,
           "settings": {"trials": args.trials, "seed": args.seed}, "conditions": {}}
    for rate, ref_file in REFERENCES.items():
        t0 = time.time()
        counts = run_trials(model, exc, n_trials=args.trials, rate=rate, seed=args.seed,
                            t_run=1000.0, workers=args.workers)
        ours = counts.mean(axis=1)  # spikes per 1 s trial = Hz
        ref = reference_rates(SHIU_DIR / "results" / "example" / ref_file)
        ref_idx = c.index_of(list(ref))
        ref_vec = np.zeros(c.n)
        ref_vec[ref_idx] = list(ref.values())
        active = np.flatnonzero((ours > 0) | (ref_vec > 0))
        non_input = np.setdiff1d(active, exc)
        r = float(np.corrcoef(ours[non_input], ref_vec[non_input])[0, 1])
        top_ref = set(non_input[np.argsort(-ref_vec[non_input])[:50]].tolist())
        top_ours = set(non_input[np.argsort(-ours[non_input])[:50]].tolist())
        mn9_trials = counts[mn9].astype(float)
        cond = {
            "rate_hz": rate, "seconds": round(time.time() - t0, 1),
            "mn9_ours_hz": float(mn9_trials.mean()),
            "mn9_ours_sd": float(mn9_trials.std(ddof=1)),
            "mn9_reference_hz": float(ref.get(MN9_FLYWIRE, 0.0)),
            "active_neurons_ours": int((ours > 0).sum()),
            "active_neurons_reference": int(len(ref)),
            "pearson_r_non_input": r,
            "top50_overlap": len(top_ref & top_ours),
            "sugar_grn_rate_ours": float(ours[exc].mean()),
            "sugar_grn_rate_reference": float(np.mean([ref.get(i, 0.0) for i in SUGAR_R])),
            "per_neuron": {"index": non_input.tolist(), "ours": ours[non_input].tolist(),
                           "reference": ref_vec[non_input].tolist(),
                           "flywire_id": c.ids[non_input].tolist()},
        }
        out["conditions"][str(int(rate))] = cond
        print(f"{rate:.0f} Hz: MN9 ours {cond['mn9_ours_hz']:.1f} ± {cond['mn9_ours_sd']:.1f} vs "
              f"reference {cond['mn9_reference_hz']:.1f}; active {cond['active_neurons_ours']} vs "
              f"{cond['active_neurons_reference']}; r = {r:.3f}; top-50 overlap "
              f"{cond['top50_overlap']}/50; {cond['seconds']}s", flush=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = started["utc"][:19].replace("-", "").replace(":", "")
    path = args.out_dir / f"shiu_repro_{stamp}Z_{started['git_rev']}.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print("WROTE", path)


if __name__ == "__main__":
    main()
