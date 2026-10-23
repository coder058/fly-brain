"""EXP-E2-HD: does the fly head-direction circuit's real wiring hold a position in memory?

Task: a brief current pulse goes into the EPG neurons of one right-hemisphere protocerebral
bridge glomerulus (R1..R8, 8 classes, chance 0.125). After the pulse the network gets only
noise. A ridge readout must name the stimulated glomerulus from spiking in a short window at
each delay. The readout never sees any neuron that can receive the pulse (all right-side
EPGs), so it can only succeed through activity the network itself carries.

Arms: connectome; a degree-preserving null that keeps Dale's law; a block-preserving null that
also keeps every cell-type-to-cell-type edge count and destroys only the topographic map.

Fairness is an equal tuning budget, not matched firing rate: an exploratory pilot (dev seeds
0-1) showed this circuit is bistable under the LIF model -- silent after the pulse below a
critical gain, near-saturated above it -- so rate matching would park every arm on a cliff.
Every graph is simulated on the same gain grid and, per delay, the gain with the best
validation accuracy on training trials is tested once.
"""
from __future__ import annotations

import os

for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import hashlib
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
from scipy import sparse, stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import e1_reservoir as H
from flylab.dynamics import LIFParams, LIFState, step_lif
from flylab.nulls import block_preserving_null, degree_preserving_null
from flylab.slice import load_hd_circuit
from flylab.spectral import spectral_radius, syn_scale_for_gain

ROOT = HERE.parents[1]
GLOMERULI = [f"R{k}" for k in range(1, 9)]
NULL_STREAM = 70_000


def build_task(neurons):
    """Input sets per class and the readout pool (everything that can never be an input)."""
    types = neurons["type"].to_numpy()
    glom = neurons["pb_glomerulus"].to_numpy()
    inputs = [np.flatnonzero((types == "EPG") & (glom == g)) for g in GLOMERULI]
    if any(len(i) == 0 for i in inputs):
        raise RuntimeError("a glomerulus has no EPG neuron")
    candidate = np.unique(np.concatenate(inputs))
    pool = np.setdiff1d(np.arange(len(neurons)), candidate)
    return inputs, candidate, pool


def make_labels(n_classes, trials_per_class, rng):
    labels = np.repeat(np.arange(n_classes), trials_per_class)
    rng.shuffle(labels)
    return labels


def run_trial(W, lif, label, inputs, cfg, n, trial_seed, record_steps):
    """Simulate one trial; return spikes at the requested absolute steps (dict step -> vec)."""
    rng = np.random.default_rng(trial_seed)
    T = cfg["pulse_steps"] + max(cfg["delays"]) + cfg["window"]
    state = LIFState(v=rng.normal(0.0, 0.05, size=n).astype(np.float32),
                     spikes=np.zeros(n, dtype=np.float32))
    out = {}
    total = np.zeros(n, dtype=np.float32)  # spikes after the pulse only
    for t in range(T):
        I = rng.normal(0.0, cfg["noise"], size=n).astype(np.float32)
        if t < cfg["pulse_steps"]:
            I[inputs[label]] += cfg["pulse_amp"]
        state = step_lif(W, state, I, lif)
        if t >= cfg["pulse_steps"]:
            total += state.spikes
        if t in record_steps:
            out[t] = state.spikes.copy()
    return out, total


def features(W, lif, labels, inputs, pool, cfg, seed, trial_ids=None):
    """Per delay: mean pool spikes over the `window` steps ending at pulse end + delay.

    Each trial's noise depends only on (seed, trial id), so a trial gets the same noise
    whether it is simulated for gain matching (training trials only) or for evaluation.
    The returned rate is the pool's firing rate during the delay period (after the pulse),
    the activity a memory has to live in.
    """
    trial_ids = np.arange(len(labels)) if trial_ids is None else np.asarray(trial_ids)
    n = W.shape[0]
    P, win = cfg["pulse_steps"], cfg["window"]
    steps = {d: list(range(P + d - win + 1, P + d + 1)) for d in cfg["delays"]}
    record = set(s for v in steps.values() for s in v)
    X = {d: np.zeros((len(labels), len(pool)), dtype=np.float32) for d in cfg["delays"]}
    delay_spikes = 0.0
    for i, lab in enumerate(labels):
        rec, total = run_trial(W, lif, lab, inputs, cfg, n, [seed, int(trial_ids[i])], record)
        for d, ss in steps.items():
            X[d][i] = np.mean([rec[s][pool] for s in ss], axis=0)
        delay_spikes += float(total[pool].sum())
    T = max(cfg["delays"]) + win
    rate = delay_spikes / (len(labels) * T * len(pool))
    return X, rate


def lif_for(rho, gain, cfg):
    tau = cfg["tau_m"]
    scale = syn_scale_for_gain(rho, gain, tau) if rho > 0 else 0.0  # no_network: W = 0
    return LIFParams(tau_m=tau, v_th=1.0, dt=1.0, syn_scale=scale)


_STATE: dict = {}


def split(labels, seed):
    """70/30 within-class split, fixed per seed."""
    rng = np.random.default_rng([seed, 2])
    idx = np.arange(len(labels))
    tr, te = [], []
    for c in np.unique(labels):
        ci = rng.permutation(idx[labels == c])
        cut = int(0.7 * len(ci))
        tr += ci[:cut].tolist()
        te += ci[cut:].tolist()
    return np.array(tr), np.array(te)


def run_seed(seed):
    """Equal tuning budget: every graph is simulated at every gain on the grid; for each delay
    the gain is chosen by validation accuracy on training trials only, then tested once."""
    cfg, graphs, rhos = _STATE["cfg"], _STATE["graphs"], _STATE["rhos"]
    inputs, pool = _STATE["inputs"], _STATE["pool"]
    labels = make_labels(len(inputs), cfg["trials_per_class"], np.random.default_rng([seed, 1]))
    tr, te = split(labels, seed)
    rows = []
    for arm, Ws in graphs.items():
        for d_i, W in enumerate(Ws):
            rho = rhos[arm][d_i]
            per_gain = []
            for g in cfg["gains"]:
                X, rate = features(W, lif_for(rho, g, cfg), labels, inputs, pool, cfg, seed)
                per_gain.append((g, X, rate))
            for d in cfg["delays"]:
                best = None
                for g, X, rate in per_gain:
                    Xd = X[d]
                    if not np.isfinite(Xd).all() or len(np.unique(np.round(Xd[tr], 6), axis=0)) < 10:
                        continue  # silent or degenerate at this gain: not a candidate
                    r = H.ridge_sweep(Xd[tr], labels[tr], Xd[te], labels[te], len(inputs), seed=seed)
                    val = max(c["val_acc"] for c in r["curve"])
                    if best is None or val > best["val_acc"]:
                        best = {"gain": g, "val_acc": val, "acc": r["acc"], "rate": rate}
                rows.append({"seed": seed, "arm": arm, "draw": d_i, "delay": d,
                             **(best or {"gain": None, "val_acc": None, "acc": None, "rate": None}),
                             "rates_by_gain": [float(r) for _, _, r in per_gain]})
    print(f"  seed {seed} done", flush=True)
    return rows


def summarise(rows, seeds, delays, arms):
    valid = lambda r: r["acc"] is not None
    out = {}
    for d in delays:
        per = {}
        for s in seeds:
            per[s] = {}
            for a in arms:
                v = [r["acc"] for r in rows if r["seed"] == s and r["delay"] == d and r["arm"] == a and valid(r)]
                per[s][a] = float(np.mean(v)) if v else None
        cell = {"means": {}, "comparisons": {}}
        for a in arms:
            v = [p[a] for p in per.values() if p[a] is not None]
            cell["means"][a] = {"mean": float(np.mean(v)) if v else None, "n": len(v)}
        for a in arms[1:]:
            diff = np.array([p[arms[0]] - p[a] for p in per.values()
                             if p[arms[0]] is not None and p[a] is not None])
            if len(diff) > 1:
                h = float(stats.t.ppf(0.975, len(diff) - 1) * diff.std(ddof=1) / np.sqrt(len(diff)))
                cell["comparisons"][f"{arms[0]}_vs_{a}"] = {
                    "mean": float(diff.mean()), "ci95": [float(diff.mean() - h), float(diff.mean() + h)],
                    "n": int(len(diff)), "per_seed": diff.tolist()}
        out[str(d)] = cell
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", required=True, help="a:b range (b exclusive) or comma list")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "experiments/results/EXP-E2-HD")
    ap.add_argument("--draws", type=int, default=10)
    ap.add_argument("--trials-per-class", type=int, default=40)
    ap.add_argument("--delays", default="5,15,30,60")
    ap.add_argument("--window", type=int, default=5)
    ap.add_argument("--pulse-steps", type=int, default=5)
    ap.add_argument("--pulse-amp", type=float, default=4.0)
    ap.add_argument("--noise", type=float, default=0.6)
    ap.add_argument("--gains", default="1,1.5,2,2.5,3,3.5,4,5,6,8,12,16",
                    help="fixed tuning grid, identical for every graph")
    ap.add_argument("--tau-m", type=float, default=6.0)
    ap.add_argument("--swaps-per-edge", type=int, default=10)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    seeds = (list(range(*map(int, args.seeds.split(":")))) if ":" in args.seeds
             else [int(s) for s in args.seeds.split(",")])
    started = {**H.provenance(), "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]}
    t0 = time.time()
    cfg = {"delays": [int(d) for d in args.delays.split(",")], "window": args.window,
           "pulse_steps": args.pulse_steps, "pulse_amp": args.pulse_amp, "noise": args.noise,
           "tau_m": args.tau_m, "gains": [float(g) for g in args.gains.split(",")],
           "trials_per_class": args.trials_per_class}
    sl, neurons = load_hd_circuit()
    inputs, candidate, pool = build_task(neurons)
    labels_type = neurons["type"].to_numpy()
    graphs = {"connectome": [sl.W()], "dale_degree_null": [], "topography_null": []}
    for d in range(args.draws):
        Wd, _ = degree_preserving_null(sl.src, sl.dst, sl.signed_weight, sl.n,
                                       np.random.default_rng([NULL_STREAM, d]),
                                       args.swaps_per_edge, weights_follow="pre")
        graphs["dale_degree_null"].append(Wd)
        Wb, _ = block_preserving_null(sl.src, sl.dst, sl.signed_weight, sl.n, labels_type,
                                      np.random.default_rng([NULL_STREAM + 1, d]), args.swaps_per_edge)
        graphs["topography_null"].append(Wb)
    # Calibration arm: no recurrent connections at all. The readout never sees an input
    # neuron, so this must sit at chance; if it does not, the task leaks.
    graphs["no_network"] = [sparse.csr_matrix((sl.n, sl.n), dtype=np.float32)]
    rhos = {k: [spectral_radius(W) if W.nnz else 0.0 for W in v] for k, v in graphs.items()}
    _STATE.update(cfg=cfg, graphs=graphs, rhos=rhos, inputs=inputs, pool=pool)
    print(f"ready at {time.time() - t0:.0f}s: n={sl.n}, pool={len(pool)}, inputs per class "
          f"{[len(i) for i in inputs]}", flush=True)
    if args.workers == 1:
        rows = [r for s in seeds for r in run_seed(s)]
    else:
        with mp.get_context("fork").Pool(args.workers) as p:
            rows = [r for chunk in p.map(run_seed, seeds, chunksize=1) for r in chunk]
    arms = list(graphs)
    summary = summarise(rows, seeds, cfg["delays"], arms)
    res = {"experiment": "EXP-E2-HD", "label": args.label, "provenance": started,
           "settings": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
           "cfg": cfg, "seeds": seeds, "n_pool": int(len(pool)),
           "summary": summary, "rows": rows, "seconds": time.time() - t0}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = started["utc"][:19].replace("-", "").replace(":", "")
    out = args.out_dir / f"hd_{args.label}_{stamp}Z_{started['git_rev']}.json"
    if out.exists():
        raise RuntimeError(f"refusing to overwrite {out}")
    out.write_text(json.dumps(res, indent=1) + "\n")
    for d, cell in summary.items():
        means = "  ".join(f"{a}={v['mean']:.3f}(n={v['n']})" for a, v in cell["means"].items()
                          if v["mean"] is not None)
        print(f"delay {d:>3}: {means}")
        for k, c in cell["comparisons"].items():
            print(f"           {k}: {c['mean']:+.3f} [{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}] n={c['n']}")
    print(f"total {res['seconds']:.0f}s\nWROTE {out}", flush=True)


if __name__ == "__main__":
    main()
