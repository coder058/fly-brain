"""EXP-W1-SUGAR: does Shiu et al.'s sugar -> MN9 prediction replicate on another connectome?

Shiu et al. (Nature 2024) activated labellar sugar gustatory receptor neurons in a
whole-brain LIF model built on FlyWire and predicted that MN9, the motor neuron that drives
proboscis extension, fires. This runner applies the identical model (flylab.brain,
spike-for-spike equivalent to their Brian 2 code; their published simulations reproduced in
SHIU-REPRO) to the MaleCNS v1.0 connectome: a different animal, the other sex, and a CNS
that includes the ventral nerve cord.

Inputs are defined by cell type so that they mean the same thing in both connectomes:
LB3c, the labellar GRN type annotated "sugar" in FlyWire (Schlegel et al. 2024) and named
identically in MaleCNS. Outputs: MN9 (FlyWire 720575940660219265; MaleCNS MN9_L and MN9_R)
and the mean rate of every cell type.
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
from flylab.brain import BrainModel, run_trials  # noqa: E402
from flylab.connectomes import load_flywire_630, load_malecns_shiu_signs  # noqa: E402
from flylab.nulls import fast_dale_degree_null  # noqa: E402
from shiu_reproduction import MN9_FLYWIRE, SUGAR_R  # noqa: E402

FLYWIRE_ANN = Path("/home/user/flyconnectome/flywire_annotations/supplemental_files/"
                   "Supplemental_file1_neuron_annotations.tsv")
NULL_STREAM = 80_000


def flywire_types(c) -> np.ndarray:
    """FlyWire cell_type per neuron of the 630 table (empty where the root ID is not in the
    published annotation release)."""
    import pandas as pd

    path = Path(os.environ.get("FLYWIRE_ANNOTATIONS", FLYWIRE_ANN))
    a = pd.read_csv(path, sep="\t", usecols=["root_id", "cell_type", "hemibrain_type", "side"],
                    dtype={"root_id": "int64"}, keep_default_na=False)
    t = dict(zip(a["root_id"], np.where(a["cell_type"] != "", a["cell_type"], a["hemibrain_type"]),
                 strict=True))
    side = dict(zip(a["root_id"], a["side"], strict=True))
    types = np.array([t.get(int(i), "") for i in c.ids], dtype=object)
    sides = np.array([side.get(int(i), "") for i in c.ids], dtype=object)
    return types, sides


def malecns_types(c):
    import pyarrow.feather as feather

    a = feather.read_table(ROOT / "data/derived/graph/neurons.feather",
                           columns=["body_id", "type", "rootSide", "somaSide"]).to_pandas()
    assert (a["body_id"].to_numpy() == c.ids).all()
    side = a["rootSide"].fillna(a["somaSide"]).fillna("").to_numpy(dtype=object)
    return a["type"].fillna("").to_numpy(dtype=object), side


def inputs_for(name, c, types, sides):
    if name == "shiu21":
        return c.index_of(SUGAR_R)
    if name.startswith("lb3c"):
        idx = np.flatnonzero(types == "LB3c")
        if name.endswith("_L"):
            idx = idx[np.isin(sides[idx], ["L", "left"])]
        elif name.endswith("_R"):
            idx = idx[np.isin(sides[idx], ["R", "right"])]
        return idx
    raise ValueError(name)


def mn9_index(c, types):
    if c.name.startswith("FlyWire"):
        return c.index_of([MN9_FLYWIRE])
    idx = np.flatnonzero(types == "MN9")
    assert len(idx) == 2, idx
    return idx


def type_rates(rates, types, exclude):
    mask = np.ones(len(rates), dtype=bool)
    mask[exclude] = False
    mask &= types != ""
    out = {}
    for t in np.unique(types[mask]):
        sel = mask & (types == t)
        out[str(t)] = float(rates[sel].mean())
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--connectome", choices=("malecns", "flywire"), required=True)
    ap.add_argument("--inputs", default="lb3c_both")
    ap.add_argument("--rates", default="0,50,100,150,200")
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--null-draws", type=int, default=0, help="Dale degree nulls at the top rate")
    ap.add_argument("--seed", type=int, default=7000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "experiments/results/EXP-W1-SUGAR")
    args = ap.parse_args(argv)
    started = {**H.provenance(),
               "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]}
    c = load_malecns_shiu_signs() if args.connectome == "malecns" else load_flywire_630()
    types, sides = malecns_types(c) if args.connectome == "malecns" else flywire_types(c)
    mn9 = mn9_index(c, types)
    rates = [float(r) for r in args.rates.split(",")]
    res = {"experiment": "EXP-W1-SUGAR", "label": args.label, "provenance": started,
           "connectome": c.name, "connectome_meta": c.meta, "settings": vars(args) | {"out_dir": str(args.out_dir)},
           "mn9_index": mn9.tolist(), "conditions": {}}
    model = BrainModel(c.W)
    for inp in args.inputs.split(","):
        exc = inputs_for(inp, c, types, sides)
        for r in rates:
            t0 = time.time()
            counts = run_trials(model, exc, n_trials=args.trials, rate=r, seed=args.seed,
                                t_run=1000.0, workers=args.workers)
            mn9_trials = counts[mn9].mean(axis=0).astype(float)  # mean of the MN9s, per trial
            per_neuron = counts.mean(axis=1)
            key = f"{inp}@{int(r)}"
            res["conditions"][key] = {
                "input": inp, "n_inputs": int(len(exc)), "rate_hz": r,
                "mn9_trials": mn9_trials.tolist(),
                "mn9_each": counts[mn9].mean(axis=1).tolist(),
                "mn9_mean": float(mn9_trials.mean()),
                "active_neurons": int((per_neuron > 0).sum()),
                "type_rates": type_rates(per_neuron, types, exc) if r == max(rates) else None,
                "seconds": round(time.time() - t0, 1)}
            print(f"{c.name} {key}: n_in={len(exc)} MN9 {mn9_trials.mean():.1f} Hz "
                  f"(each {np.round(counts[mn9].mean(axis=1), 1).tolist()}) active "
                  f"{int((per_neuron > 0).sum())} [{time.time() - t0:.0f}s]", flush=True)
        for d in range(args.null_draws if inp == args.inputs.split(",")[0] else 0):
            C = c.W.tocoo()
            keep = C.row != C.col
            Wn, diag = fast_dale_degree_null(C.col[keep], C.row[keep], C.data[keep], c.n,
                                             np.random.default_rng([NULL_STREAM, d]))
            r = max(rates)
            counts = run_trials(BrainModel(Wn), exc, n_trials=args.trials, rate=r,
                                seed=args.seed, t_run=1000.0, workers=args.workers)
            mn9_trials = counts[mn9].mean(axis=0).astype(float)
            res["conditions"][f"{inp}@{int(r)}/dale_null{d}"] = {
                "input": inp, "rate_hz": r, "null_draw": d, "null_diag": diag,
                "mn9_trials": mn9_trials.tolist(), "mn9_mean": float(mn9_trials.mean()),
                "active_neurons": int((counts.mean(axis=1) > 0).sum())}
            print(f"  null {d}: MN9 {mn9_trials.mean():.1f} Hz", flush=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = started["utc"][:19].replace("-", "").replace(":", "")
    path = args.out_dir / f"sugar_{args.label}_{stamp}Z_{started['git_rev']}.json"
    path.write_text(json.dumps(res, indent=1) + "\n")
    print("WROTE", path)


if __name__ == "__main__":
    main()
