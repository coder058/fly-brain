"""EXP-W2-CALIB: does the sugar -> MN9 pathway survive when MaleCNS is calibrated to FlyWire's
excitability?

EXP-W1-SUGAR found the pathway on MaleCNS, but with the model's FlyWire-tuned weights about
20,500 neurons fire there against ~490 on FlyWire. Here one number, a gain `s` on every
recurrent MaleCNS weight (input drive unchanged), is calibrated so that LB3c stimulation at
200 Hz recruits as many neurons per trial as on FlyWire. The calibration looks only at how
many neurons fire, never at MN9. Then the preregistered test runs on fresh seeds.

Stages, in one process with a checkpoint after each condition:
1. FlyWire reference: mean number of neurons firing >= 1 spike per trial (4 trials).
2. Calibration: geometric bisection of s in [0.05, 0.59], 8 steps, 4 trials each; the
   evaluated s with the smallest |log(active / reference)| is kept.
3. Confirmation at that s: rates 0..200 Hz, 30 trials, 3 Dale degree nulls (also scaled).
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

import e1_reservoir as H  # noqa: E402
import sugar_mn9 as S  # noqa: E402
from flylab.brain import BrainModel, run_trials  # noqa: E402
from flylab.connectomes import load_flywire_630, load_malecns_shiu_signs  # noqa: E402
from flylab.nulls import fast_dale_degree_null  # noqa: E402

CALIB_SEED = 9000
CONFIRM_SEED = 7100
NULL_STREAM = 81_000
CALIB_RATE = 200.0


def per_trial_active(counts: np.ndarray) -> float:
    """Mean over trials of the number of neurons that spike at least once in that trial."""
    return float((counts > 0).sum(axis=0).mean())


def bisect_scale(measure, target: float, lo: float = 0.05, hi: float = 0.59, steps: int = 8):
    """Geometric bisection for the gain whose activity matches `target` (activity is assumed
    to grow with the gain). Returns (best_s, history)."""
    hist = []
    for _ in range(steps):
        s = float(np.sqrt(lo * hi))
        a = measure(s)
        hist.append({"scale": s, "active_per_trial": a})
        if a > target:
            hi = s
        else:
            lo = s
    best = min(hist, key=lambda h: abs(np.log(max(h["active_per_trial"], 1.0) / target)))
    return best["scale"], hist


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rates", default="0,50,100,150,200")
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--calib-trials", type=int, default=4)
    ap.add_argument("--null-draws", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "experiments/results/EXP-W2-CALIB")
    args = ap.parse_args(argv)
    started = {**H.provenance(),
               "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = started["utc"][:19].replace("-", "").replace(":", "")
    path = args.out_dir / f"calib_{stamp}Z_{started['git_rev']}.json"
    res = {"experiment": "EXP-W2-CALIB", "provenance": started, "complete": False,
           "settings": vars(args) | {"out_dir": str(args.out_dir)}, "conditions": {}}

    def checkpoint():
        path.write_text(json.dumps(res, indent=1) + "\n")

    fw = load_flywire_630()
    ft, fs = S.flywire_types(fw)
    exc = S.inputs_for("lb3c_both", fw, ft, fs)
    counts = run_trials(BrainModel(fw.W), exc, n_trials=args.calib_trials, rate=CALIB_RATE,
                        seed=CALIB_SEED, t_run=1000.0, workers=args.workers)
    target = per_trial_active(counts)
    res["flywire_reference_active_per_trial"] = target
    print(f"FlyWire reference: {target:.1f} neurons fire per trial", flush=True)
    checkpoint()
    del fw

    mc = load_malecns_shiu_signs()
    mt, ms = S.malecns_types(mc)
    exc = S.inputs_for("lb3c_both", mc, mt, ms)
    mn9 = S.mn9_index(mc, mt)

    def measure(s):
        t0 = time.time()
        c = run_trials(BrainModel(mc.W * s), exc, n_trials=args.calib_trials, rate=CALIB_RATE,
                       seed=CALIB_SEED, t_run=1000.0, workers=args.workers)
        a = per_trial_active(c)
        print(f"  calib s={s:.4f}: {a:.0f} neurons/trial [{time.time() - t0:.0f}s]", flush=True)
        return a

    scale, hist = bisect_scale(measure, target)
    res["calibration"] = {"history": hist, "scale": scale, "target": target}
    print(f"calibrated scale {scale:.4f}", flush=True)
    checkpoint()

    model = BrainModel(mc.W * scale)
    rates = [float(r) for r in args.rates.split(",")]
    for r in rates:
        t0 = time.time()
        counts = run_trials(model, exc, n_trials=args.trials, rate=r, seed=CONFIRM_SEED,
                            t_run=1000.0, workers=args.workers)
        mn9_trials = counts[mn9].mean(axis=0).astype(float)
        per_neuron = counts.mean(axis=1)
        res["conditions"][f"lb3c_both@{int(r)}"] = {
            "input": "lb3c_both", "rate_hz": r, "n_inputs": int(len(exc)),
            "mn9_trials": mn9_trials.tolist(), "mn9_each": counts[mn9].mean(axis=1).tolist(),
            "mn9_mean": float(mn9_trials.mean()), "active_neurons": int((per_neuron > 0).sum()),
            "active_per_trial": per_trial_active(counts),
            "type_rates": S.type_rates(per_neuron, mt, exc) if r == max(rates) else None,
            "seconds": round(time.time() - t0, 1)}
        print(f"MaleCNS x{scale:.4f} lb3c_both@{int(r)}: MN9 {mn9_trials.mean():.1f} Hz "
              f"(each {np.round(counts[mn9].mean(axis=1), 1).tolist()}) active "
              f"{int((per_neuron > 0).sum())} [{time.time() - t0:.0f}s]", flush=True)
        checkpoint()
    C = mc.W.tocoo()
    keep = C.row != C.col
    for d in range(args.null_draws):
        Wn, diag = fast_dale_degree_null(C.col[keep], C.row[keep], C.data[keep], mc.n,
                                         np.random.default_rng([NULL_STREAM, d]))
        counts = run_trials(BrainModel(Wn * scale), exc, n_trials=args.trials, rate=max(rates),
                            seed=CONFIRM_SEED, t_run=1000.0, workers=args.workers)
        mn9_trials = counts[mn9].mean(axis=0).astype(float)
        res["conditions"][f"lb3c_both@{int(max(rates))}/dale_null{d}"] = {
            "input": "lb3c_both", "rate_hz": max(rates), "null_draw": d, "null_diag": diag,
            "mn9_trials": mn9_trials.tolist(), "mn9_mean": float(mn9_trials.mean()),
            "active_neurons": int((counts.mean(axis=1) > 0).sum())}
        print(f"  null {d}: MN9 {mn9_trials.mean():.1f} Hz", flush=True)
        checkpoint()
    res["complete"] = True
    checkpoint()
    print("WROTE", path)


if __name__ == "__main__":
    main()
