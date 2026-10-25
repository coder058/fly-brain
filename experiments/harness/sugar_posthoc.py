"""EXP-W1-SUGAR exploratory follow-ups (post hoc, not preregistered).

1. Silencing the shared disynaptic interneuron. The shortest LB3c -> MN9 path is
   LB3c -> CB0573 -> MN9 in FlyWire and LB3c -> GNG043 -> MN9 in MaleCNS, and MaleCNS
   annotates GNG043 as the FlyWire type CB0573. Silencing it (and, in MaleCNS, the other
   two-hop candidate DNge031) asks how much of MN9's drive runs through it.
2. Synaptic-scale sensitivity. w_syn = 0.275 mV was tuned on FlyWire. MaleCNS reports 1.69x
   more input synapses per neuron (median 349 vs 206), and the transferred model activates
   ~20,000 neurons where FlyWire activates ~450. Rerun MaleCNS with w_syn scaled by 206/349.
3. Histamine sign. FlyWire's transmitter classifier has no histamine class and Shiu et al.'s
   rule makes histamine excitatory, but it gates chloride channels in flies. In MaleCNS it is
   almost only photoreceptors and optic-lobe cells, plus the shared interneuron GNG043
   (FlyWire: CB0573, "dopamine"). Rerun MaleCNS with histamine inhibitory.
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
from flylab.brain import DEFAULTS, BrainModel, run_trials  # noqa: E402
from flylab.connectomes import load_flywire_630, load_malecns_shiu_signs  # noqa: E402

SCALE = 206 / 349  # FlyWire / MaleCNS median input synapses per neuron


def run(c, types, sides, label, exc, rate, silence=(), w_syn=None, trials=30, workers=4,
        seed=7000):
    params = dict(DEFAULTS)
    if w_syn is not None:
        params["w_syn"] = w_syn
    t0 = time.time()
    counts = run_trials(BrainModel(c.W, params), exc, n_trials=trials, rate=rate, seed=seed,
                        t_run=1000.0, silence=silence, workers=workers)
    mn9 = S.mn9_index(c, types)
    mt = counts[mn9].mean(axis=0).astype(float)
    row = {"label": label, "connectome": c.name, "rate_hz": rate, "w_syn": params["w_syn"],
           "silenced_types": sorted(set(types[list(silence)].tolist())) if len(silence) else [],
           "n_silenced": int(len(silence)), "mn9_trials": mt.tolist(), "mn9_mean": float(mt.mean()),
           "mn9_each": counts[mn9].mean(axis=1).tolist(),
           "active_neurons": int((counts.mean(axis=1) > 0).sum()), "seconds": round(time.time() - t0, 1)}
    print(f"{c.name} {label}: MN9 {row['mn9_mean']:.1f} Hz (each {np.round(row['mn9_each'], 1).tolist()}) "
          f"active {row['active_neurons']} [{row['seconds']}s]", flush=True)
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=ROOT / "experiments/results/EXP-W1-SUGAR")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    started = {**H.provenance(),
               "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]}
    rows = []
    fw = load_flywire_630()
    ft, fs = S.flywire_types(fw)
    exc = S.inputs_for("lb3c_both", fw, ft, fs)
    rows.append(run(fw, ft, fs, "lb3c_both@200 silence CB0573", exc, 200.0,
                    silence=np.flatnonzero(ft == "CB0573"), workers=args.workers))
    del fw
    mc = load_malecns_shiu_signs()
    mt, ms = S.malecns_types(mc)
    exc = S.inputs_for("lb3c_both", mc, mt, ms)
    for t in ("GNG043", "DNge031"):
        rows.append(run(mc, mt, ms, f"lb3c_both@200 silence {t}", exc, 200.0,
                        silence=np.flatnonzero(mt == t), workers=args.workers))
    for r in (0.0, 200.0):
        rows.append(run(mc, mt, ms, f"lb3c_both@{int(r)} w_syn x {SCALE:.3f}", exc, r,
                        w_syn=DEFAULTS["w_syn"] * SCALE, workers=args.workers))
    del mc
    mh = load_malecns_shiu_signs(inhibitory=("gaba", "glutamate", "histamine"))
    for r in (0.0, 200.0):
        rows.append(run(mh, mt, ms, f"lb3c_both@{int(r)} histamine inhibitory", exc, r,
                        workers=args.workers))
    out = {"experiment": "EXP-W1-SUGAR", "label": "posthoc", "preregistered": False,
           "provenance": started, "rows": rows}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = started["utc"][:19].replace("-", "").replace(":", "")
    path = args.out_dir / f"sugar_posthoc_{stamp}Z_{started['git_rev']}.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print("WROTE", path)


if __name__ == "__main__":
    main()
