"""Positive control: a gate, not a report.

Two conditions that a working instrument MUST separate:

  PC-A  activity resolution   same graph, quiescent gain vs ignited gain.
  PC-B  structure resolution  ring lattice (a delay line) vs Erdos-Renyi, same n, same
                              edge count, same weight distribution, all-excitatory in both,
                              and gain tuned per graph so their non-input firing rates match.
                              Only topology differs.

If either fails, the harness cannot resolve differences it obviously should, and no
connectome-vs-null number it produces is worth reading. In that case STOP.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import e1_reservoir as H
from flylab.dynamics import LIFParams, post_pre_from_pre_post
from flylab.graph import load_graph, induced_subgraph
from flylab.nulls import er_graph, ring_lattice
from flylab.spectral import gain_for_target_rate, spectral_radius, syn_scale_for_gain

MIN_EFFECT = 0.10  # minimum mean accuracy gap that counts as "separated"


def paired_stats(a, b):
    """Paired over seeds: both conditions see the same trials for a given seed."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    n = len(d)
    se = d.std(ddof=1) / np.sqrt(n) if n > 1 else 0.0
    ci = 1.96 * se
    return {
        "mean_a": float(np.mean(a)), "mean_b": float(np.mean(b)),
        "mean_diff": float(d.mean()), "ci95_diff": float(ci),
        "per_seed_diff": [float(x) for x in d],
        "ci_excludes_zero": bool(abs(d.mean()) > ci) if n > 1 else False,
        "n_seeds": n,
    }


def verdict(st, min_effect=MIN_EFFECT):
    passed = abs(st["mean_diff"]) >= min_effect and st["ci_excludes_zero"]
    return {**st, "min_effect": min_effect, "separated": bool(passed)}


def pc_b_verdict(details):
    invalid = [d["seed"] for d in details if (
        d["ring"]["acc"] is None or d["er"]["acc"] is None
        or not d["ring"]["matched"] or not d["er"]["matched"]
    )]
    if invalid:
        # A dead reservoir or failed rate match cannot count as structural resolution.
        return {"mean_a": None, "mean_b": None, "mean_diff": None,
                "ci95_diff": None, "per_seed_diff": [], "ci_excludes_zero": False,
                "n_seeds": len(details), "min_effect": MIN_EFFECT,
                "separated": False, "valid": False, "invalid_seeds": invalid}
    st = paired_stats([d["ring"]["acc"] for d in details],
                      [d["er"]["acc"] for d in details])
    return {**verdict(st), "valid": True}


def score(W, rho, I_list, y, tr, te, inputs, cfg, gain, seed, n_probes,
          require_live=False):
    """rho is passed in because a dense eigendecomposition per bisection step dominates cost."""
    base = cfg["dynamics"]["lif"]
    ss = syn_scale_for_gain(rho, gain, base["tau_m"], base.get("dt", 1.0))
    lif = LIFParams(**{**base, "syn_scale": ss})
    X, st = H.reservoir_features(W, I_list, lif, seed, input_ids=inputs, n_probes=n_probes)
    if require_live:
        liveness = H.check_alive(X, st, "positive_control", cfg.get("harness_guards", {}))
        st["liveness"] = liveness
        if not liveness["alive"]:
            return None, st, ss
    acc = H.accuracy(
        H.predict(H.fit_readout(X[tr], y[tr], cfg["dynamics"]["n_classes"]), X[te]), y[te]
    )
    return acc, st, ss


def spike_rate(W, rho, I_list, inputs, cfg, gain, seed, n_pool):
    """Bulk firing rate only, so the gain bisection can run on a trial subsample."""
    base = cfg["dynamics"]["lif"]
    ss = syn_scale_for_gain(rho, gain, base["tau_m"], base.get("dt", 1.0))
    lif = LIFParams(**{**base, "syn_scale": ss})
    _, st = H.reservoir_features(W, I_list, lif, seed, input_ids=inputs, n_probes=8)
    return st["pool_spikes"] / (len(I_list) * cfg["dynamics"]["n_steps"] * n_pool)


def main(argv=None):
    ap = argparse.ArgumentParser(description="E1 positive control gate")
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--quiescent-gain", type=float, default=0.3)
    ap.add_argument("--ignited-gain", type=float, default=12.0)
    ap.add_argument("--target-rate", type=float, default=0.01,
                    help="non-input spikes per neuron-step to match PC-B conditions at")
    ap.add_argument("--n-probes", type=int, default=450)
    ap.add_argument("--n-trials", type=int, default=0,
                    help="override trials per class (0 = use config)")
    ap.add_argument("--match-trials", type=int, default=20,
                    help="trials used for the gain bisection; firing rate is a bulk property")
    ap.add_argument("--prefix", default="e1_positive_control")
    args = ap.parse_args(argv)

    seeds = [int(s) for s in args.seeds.split(",")]
    cfg = H.load_cfg()
    cfg.setdefault("harness_guards", {})["on_dead"] = "record"
    if args.n_trials:
        cfg["dynamics"]["n_trials_per_class"] = args.n_trials
    print("loading graph...", flush=True)
    g = load_graph(load_neurons=False)
    nodes = H.select_nodes(g, cfg["subgraph"]["n"])
    A, nodes = induced_subgraph(g, nodes)
    W_conn = post_pre_from_pre_post(A)
    n, nnz = A.shape[0], int(W_conn.nnz)
    n_steps = cfg["dynamics"]["n_steps"]

    pc_a = {"quiescent": [], "ignited": [], "detail": []}
    pc_b = {"ring": [], "er": [], "detail": []}
    rho_conn = spectral_radius(W_conn)

    for seed in seeds:
        rng = np.random.default_rng(seed)
        I_list, y, inputs = H.make_trials(n, cfg, rng)
        tr, te = [], []
        for c in np.unique(y):
            idx = np.where(y == c)[0]
            cut = int(0.7 * len(idx))
            tr.extend(idx[:cut].tolist())
            te.extend(idx[cut:].tolist())
        tr, te = np.array(tr), np.array(te)
        n_pool = n - len(inputs)
        denom = len(I_list) * n_steps * n_pool

        # PC-A: same graph, two operating points.
        aq, sq, ssq = score(W_conn, rho_conn, I_list, y, tr, te, inputs, cfg,
                            args.quiescent_gain, seed, args.n_probes)
        ai, si, ssi = score(W_conn, rho_conn, I_list, y, tr, te, inputs, cfg,
                            args.ignited_gain, seed, args.n_probes)
        pc_a["quiescent"].append(aq)
        pc_a["ignited"].append(ai)
        pc_a["detail"].append({
            "seed": seed,
            "quiescent": {"gain": args.quiescent_gain, "syn_scale": ssq,
                          "non_input_spikes": sq["pool_spikes"], "acc": aq},
            "ignited": {"gain": args.ignited_gain, "syn_scale": ssi,
                        "non_input_spikes": si["pool_spikes"], "acc": ai},
        })
        print(f"  PC-A seed={seed} quiescent(g={args.quiescent_gain}) acc={aq:.4f} "
              f"spikes={sq['pool_spikes']:.0f} | ignited(g={args.ignited_gain}) acc={ai:.4f} "
              f"spikes={si['pool_spikes']:.0f}", flush=True)

        # PC-B: topology only. Same n, same edge count, same weight law, all excitatory.
        W_ring = ring_lattice(n, nnz, np.random.default_rng(1000 + seed))
        W_er = er_graph(n, nnz, np.random.default_rng(2000 + seed), excitatory_only=True)
        rho_ring, rho_er = spectral_radius(W_ring), spectral_radius(W_er)
        # make_trials emits all of class 0, then all of class 1, ... so a head slice is one
        # class. Stride instead, or the matched gain is tuned to a single stimulus template.
        stride = max(1, len(I_list) // max(1, args.match_trials))
        I_match = I_list[::stride]

        def rate_fn_for(W, rho):
            return lambda gain: spike_rate(W, rho, I_match, inputs, cfg, gain, seed, n_pool)

        m_ring = gain_for_target_rate(rate_fn_for(W_ring, rho_ring), args.target_rate)
        m_er = gain_for_target_rate(rate_fn_for(W_er, rho_er), args.target_rate)
        ar, sr, ssr = score(W_ring, rho_ring, I_list, y, tr, te, inputs, cfg,
                            m_ring["gain"], seed, args.n_probes, require_live=True)
        ae, se_, sse = score(W_er, rho_er, I_list, y, tr, te, inputs, cfg,
                             m_er["gain"], seed, args.n_probes, require_live=True)
        pc_b["ring"].append(ar)
        pc_b["er"].append(ae)
        pc_b["detail"].append({
            "seed": seed,
            "ring": {"gain": m_ring["gain"], "rate": sr["pool_spikes"] / denom,
                     "matched": m_ring["converged"], "non_input_spikes": sr["pool_spikes"],
                     "syn_scale": ssr, "acc": ar},
            "er": {"gain": m_er["gain"], "rate": se_["pool_spikes"] / denom,
                   "matched": m_er["converged"], "non_input_spikes": se_["pool_spikes"],
                   "syn_scale": sse, "acc": ae},
        })
        ring_acc_label = f"{ar:.4f}" if ar is not None else "INVALID"
        er_acc_label = f"{ae:.4f}" if ae is not None else "INVALID"
        print(f"  PC-B seed={seed} ring acc={ring_acc_label} rate={sr['pool_spikes']/denom:.4f} "
              f"(g={m_ring['gain']:.2f}) | er acc={er_acc_label} rate={se_['pool_spikes']/denom:.4f} "
              f"(g={m_er['gain']:.2f})", flush=True)

    v_a = verdict(paired_stats(pc_a["ignited"], pc_a["quiescent"]))
    v_b = pc_b_verdict(pc_b["detail"])
    rates = [d["ring"]["rate"] for d in pc_b["detail"]] + [d["er"]["rate"] for d in pc_b["detail"]]
    rate_spread = float(max(rates) / max(min(rates), 1e-12))
    # An all-excitatory ER graph ignites as an avalanche, so its firing rate is near
    # discontinuous in gain and cannot be matched to within tolerance. Record which way the
    # residual mismatch points: if the winner is also the *less* active condition, the
    # leftover activity difference works against the measured effect rather than explaining it.
    mean_ring_rate = float(np.mean([d["ring"]["rate"] for d in pc_b["detail"]]))
    mean_er_rate = float(np.mean([d["er"]["rate"] for d in pc_b["detail"]]))
    winner_is_quieter = bool(v_b["mean_diff"] is not None and (
        (v_b["mean_diff"] > 0 and mean_ring_rate < mean_er_rate)
        or (v_b["mean_diff"] < 0 and mean_er_rate < mean_ring_rate)
    ))
    v_b["mean_rate_ring"] = mean_ring_rate
    v_b["mean_rate_er"] = mean_er_rate
    v_b["rate_confound_opposes_effect"] = winner_is_quieter
    summary = {
        "provenance": H.provenance(),
        "config": cfg,
        "seeds": seeds,
        "n": n, "nnz": nnz, "n_probes": args.n_probes,
        "target_rate": args.target_rate,
        "pc_a_activity_resolution": {**v_a, "detail": pc_a["detail"]},
        "pc_b_structure_resolution": {**v_b, "detail": pc_b["detail"],
                                      "rate_match_spread": rate_spread},
        "gate_passed": bool(v_a["separated"] and v_b["separated"]),
    }
    out = H.write_result(summary, prefix=args.prefix)
    print("\nPC-A activity resolution:",
          json.dumps({k: v_a[k] for k in ("mean_a", "mean_b", "mean_diff", "ci95_diff",
                                          "separated")}, indent=2), flush=True)
    print("PC-B structure resolution:",
          json.dumps({k: v_b[k] for k in ("mean_a", "mean_b", "mean_diff", "ci95_diff",
                                          "separated")}, indent=2), flush=True)
    print(f"rate-match spread (max/min across conditions) = {rate_spread:.2f}x", flush=True)
    print("GATE:", "PASSED" if summary["gate_passed"] else "FAILED", flush=True)
    print("WROTE", out, flush=True)
    return 0 if summary["gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
