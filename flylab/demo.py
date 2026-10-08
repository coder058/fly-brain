"""Five-minute tour of the project on real MaleCNS data, no download needed.

    python -m flylab.demo            # full tour, ~3-5 min on a laptop
    python -m flylab.demo --quick    # CI smoke, ~1 min

Each step reproduces one finding from the case study on the bundled 500-neuron slice and
writes a figure to figures/. Accuracy numbers are not recomputed here (that takes ~30 min
across 4 cores); the last figure is drawn from the committed EXP-E1-OP result file.
"""
from __future__ import annotations

import os

for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "harness"))

import e1_reservoir as H  # noqa: E402
from null_ensemble import make_trials_for  # noqa: E402

from flylab.dynamics import LIFParams  # noqa: E402
from flylab.nulls import degree_preserving_null, er_graph  # noqa: E402
from flylab.slice import load_slice  # noqa: E402
from flylab.spectral import gain_for_target_rate, spectral_radius, syn_scale_for_gain  # noqa: E402

FIG_DIR = ROOT / "figures"
E1_OP_DIR = ROOT / "experiments" / "results" / "EXP-E1-OP"
TARGET_RATE = 0.002

# Reference categorical palette, light mode (validated slots 1-3) + neutral for baselines.
INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0", "#fcfcfb"
C_CONN, C_DP, C_ER, C_BASE = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"


def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2,
        "ytick.color": INK_2, "text.color": INK, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "figure.dpi": 110,
    })
    return plt


def header(n: int, title: str):
    print(f"\n{'-' * 78}\n[{n}] {title}\n{'-' * 78}")


def step_data(sl):
    header(1, "The data: a 500-neuron slice of a 165,122-neuron fly brain")
    meta = json.loads((ROOT / "data/e1_slice/e1_slice_500.json").read_text())
    sign = np.sign(sl.signed_weight)
    print(f"  source      {meta['source']}")
    print(f"  full graph  {meta['full_graph']['n_neurons']:,} neurons, "
          f"{meta['full_graph']['n_edges']:,} connections, "
          f"{meta['full_graph']['weight_sum']:,} synapses")
    print(f"  this slice  {sl.n} highest out-degree neurons, {len(sl.src):,} connections "
          f"(sha256 verified)")
    print(f"  edge signs  excitatory {int((sign > 0).sum()):,} | inhibitory {int((sign < 0).sum()):,}"
          f" | unknown transmitter (weight 0) {int((sign == 0).sum()):,}")


def step_null_bug(sl, plt):
    header(2, "Bug 1: the 'degree-preserving' null that silently deleted 8% of the brain")
    rng = np.random.default_rng(0)
    new_dst = sl.dst.copy()
    rng.shuffle(new_dst)
    broken = sparse.coo_matrix((np.ones(len(sl.src)), (sl.src, new_dst)), shape=(sl.n, sl.n)).tocsr()
    lost = len(sl.src) - broken.nnz
    self_loops = int((sl.src == new_dst).sum())
    _, diag = degree_preserving_null(sl.src, sl.dst, sl.signed_weight, sl.n,
                                     np.random.default_rng([90_000, 0]), 5)
    print(f"  shuffle destinations + rebuild sparse matrix: {lost:,} of {len(sl.src):,} edges merged "
          f"away ({lost / len(sl.src):.2%}), {self_loops} self-loops created")
    print(f"  directed double-edge swap (fixed):            {diag['n_edges_out']:,} edges, "
          f"degrees preserved={diag['in_degree_preserved'] and diag['out_degree_preserved']}, "
          f"{diag['fraction_edges_rewired']:.0%} rewired")
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    labels = ["Connectome", "Shuffle null\n(original)", "Edge-swap null\n(fixed)"]
    vals = [len(sl.src), broken.nnz, diag["n_edges_out"]]
    ax.barh(labels[::-1], vals[::-1], color=[C_DP, MUTED, C_CONN], height=0.55)
    ax.set_xlim(20_000, 24_500)
    for y, v in enumerate(vals[::-1]):
        ax.text(v + 60, y, f"{v:,}", va="center", color=INK, fontsize=10)
    ax.set_xlabel("distinct connections (x-axis starts at 20,000)")
    ax.set_title(f"A shuffle null that loses {lost / len(sl.src):.1%} of connections is not a null")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_null_bug.png")
    plt.close(fig)


def _rate(W, rho, gain, I_list, inputs, cfg, seed):
    base = cfg["dynamics"]["lif"]
    lif = LIFParams(**{**base, "syn_scale": syn_scale_for_gain(rho, gain, base["tau_m"])})
    _, st = H.reservoir_features(W, I_list, lif, seed, input_ids=inputs, n_probes=48)
    T = cfg["dynamics"]["n_steps"]
    return st, st["pool_spikes"] / (len(I_list) * T * (W.shape[0] - len(inputs)))


def step_rate_bug(sl, cfg, seeds, plt):
    header(3, "Bug 2: one gain for every seed, but every seed drives different neurons")
    W_conn = sl.W()
    W_er = er_graph(sl.n, W_conn.nnz, np.random.default_rng([90_001, 0]))
    out = {}
    for name, W in (("connectome", W_conn), ("ER null", W_er)):
        rho = spectral_radius(W)
        I0, _, in0, _, _ = make_trials_for(cfg, sl.n, 0)
        sub0 = I0[::15]

        def rate_fn(g, W=W, rho=rho):
            return _rate(W, rho, g, sub0, in0, cfg, 0)[1]

        gain = gain_for_target_rate(rate_fn, TARGET_RATE, lo=0.05, hi=80.0)["gain"]
        rates = []
        for s in seeds:
            I, _, inp, _, _ = make_trials_for(cfg, sl.n, s)
            rates.append(_rate(W, rho, gain, I[::15], inp, cfg, s)[1] / TARGET_RATE)
        out[name] = np.array(rates)
        print(f"  {name:<11} gain matched on seed 0 = {gain:5.2f}; firing rate on seeds "
              f"{seeds[0]}-{seeds[-1]}: {out[name].min():.2f}x to {out[name].max():.2f}x of target")
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.axhspan(0.85, 1.15, color=GRID, zorder=0)
    ax.text(len(seeds) - 0.5, 1.0, "±15% target band", ha="right", va="center", color=INK_2, fontsize=9)
    for name, color, off in (("connectome", C_CONN, -0.12), ("ER null", C_ER, 0.12)):
        ax.scatter(np.arange(len(seeds)) + off, out[name], s=46, color=color, label=name,
                   edgecolor=SURFACE, linewidth=1.5, zorder=3)
    ax.set_xticks(range(len(seeds)), [str(s) for s in seeds])
    ax.set_xlabel("task seed (each drives a different random 10% of neurons)")
    ax.set_ylabel("firing rate / target")
    ax.set_title("Matching the gain on seed 0 does not match it on seed 9")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_rate_spread.png")
    plt.close(fig)
    return out


def step_probe_bug(sl, cfg, seeds, plt):
    header(4, "Bug 3: 48 random 'probe' neurons read out activity the connectome puts elsewhere")
    import e1_operating_point as OP

    rows = {}
    for name, W in (("connectome", sl.W()),
                    ("ER null", er_graph(sl.n, sl.W().nnz, np.random.default_rng([90_001, 0])))):
        rho = spectral_radius(W)
        active_pool, active_probe = [], []
        for s in seeds:
            I, _, inp, _, _ = make_trials_for(cfg, sl.n, s)
            sub = I[::15]

            def rate_fn(g, W=W, rho=rho, sub=sub, inp=inp, s=s):
                return _rate(W, rho, g, sub, inp, cfg, s)[1]

            gain = gain_for_target_rate(rate_fn, TARGET_RATE, lo=0.05, hi=80.0)["gain"]
            base = cfg["dynamics"]["lif"]
            lif = LIFParams(**{**base, "syn_scale": syn_scale_for_gain(rho, gain, base["tau_m"])})
            feats, _ = OP.simulate_features(W, sub, lif, s, inp)
            fired = lambda X: int((X.reshape(len(X), OP.N_BINS, -1).sum(axis=(0, 1)) > 0).sum())
            active_pool.append(fired(feats["full"]))
            active_probe.append(fired(feats["probe48"]))
        rows[name] = (np.array(active_pool), np.array(active_probe))
        print(f"  {name:<11} non-input neurons that ever fire: median {int(np.median(active_pool))} of 450;"
              f" of the 48 probes: median {int(np.median(active_probe))}, min {int(np.min(active_probe))}")
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for name, color, off in (("connectome", C_CONN, -0.12), ("ER null", C_ER, 0.12)):
        ax.scatter(np.arange(len(seeds)) + off, rows[name][1], s=46, color=color, label=name,
                   edgecolor=SURFACE, linewidth=1.5, zorder=3)
    ax.set_xticks(range(len(seeds)), [str(s) for s in seeds])
    ax.set_ylim(-1, 50)
    ax.set_xlabel("task seed (gain matched per seed, same firing rate)")
    ax.set_ylabel("probes that ever fire (of 48)")
    ax.set_title("Same firing rate, but the connectome lights up a few hubs")
    ax.legend(frameon=False, loc="center right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_probe_coverage.png")
    plt.close(fig)


def latest_result(label: str) -> Path | None:
    files = sorted(E1_OP_DIR.glob(f"e1_op_{label}_*.json"))
    return files[-1] if files else None


def step_result(plt):
    header(5, "Result: the preregistered 2x2 on 24 never-seen seeds (EXP-E1-OP)")
    path = latest_result("confirmatory")
    if path is None:
        print("  no confirmatory result committed yet")
        return
    res = json.loads(path.read_text())
    print(f"  {path.relative_to(ROOT)}")
    cells = {(c["matching"], c["readout"]): c for c in res["cells"]}
    order = [("global", "probe48"), ("global", "full"), ("per_seed", "probe48"), ("per_seed", "full")]
    names = ["original\n(global gain, 48 probes)", "global gain,\nfull readout",
             "per-seed gain,\n48 probes", "per-seed gain,\nfull readout"]
    for key in order:
        c = cells[key]
        a = c["arms"]
        cmp_ = c["comparisons"].get("connectome_vs_degree_preserving_null")
        ci = (f"diff vs DP {cmp_['mean_diff']:+.3f} [{cmp_['ci95_low']:+.3f}, {cmp_['ci95_high']:+.3f}]"
              if cmp_ else "no paired comparison")
        print(f"  {key[0]:>8}/{key[1]:<7} connectome {a['connectome_signed']['mean_acc']:.3f} "
              f"(n={a['connectome_signed']['n_seeds']})  DP {a['degree_preserving_null']['mean_acc']:.3f}  "
              f"ER {a['er_null']['mean_acc']:.3f}  {ci}")
    print(f"  input-only baseline (no network at all): {res['input_only']['mean_acc']:.3f}")

    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    x = np.arange(len(order))
    for off, arm, color, label in ((-0.24, "connectome_signed", C_CONN, "connectome"),
                                   (0.0, "degree_preserving_null", C_DP, "degree-preserving null"),
                                   (0.24, "er_null", C_ER, "Erdős–Rényi null")):
        means = [cells[k]["arms"][arm]["mean_acc"] or 0.0 for k in order]
        ax.bar(x + off, means, width=0.22, color=color, label=label, zorder=2)
        for xi, k in zip(x + off, order):
            pts = cells[k]["arms"][arm]["per_seed"]
            ax.scatter(np.full(len(pts), xi), pts, s=9, color=INK, alpha=0.35, zorder=3, linewidth=0)
    ax.axhline(res["input_only"]["mean_acc"], color=C_BASE, linewidth=1.5, linestyle=(0, (5, 3)))
    ax.text(3.45, res["input_only"]["mean_acc"] + 0.012, "no network (input only)", ha="right",
            color=INK_2, fontsize=9)
    ax.axhline(0.2, color=GRID, linewidth=1)
    ax.text(-0.45, 0.205, "chance", color=INK_2, fontsize=9, va="bottom")
    ax.set_xticks(x, names, fontsize=9.5)
    ax.set_ylim(0, 1)
    ax.set_ylabel("test accuracy (5 classes)")
    ax.set_title("Fixing the instrument changes the answer, not just the error bars")
    ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=9.5)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig4_e1_op_result.png")
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fly Lab tour on real MaleCNS data")
    ap.add_argument("--quick", action="store_true", help="fewer seeds and trials (CI)")
    args = ap.parse_args(argv)
    plt = _style()
    FIG_DIR.mkdir(exist_ok=True)
    cfg = H.load_cfg()
    cfg["dynamics"]["n_trials_per_class"] = 12 if args.quick else 60
    seeds = list(range(4)) if args.quick else list(range(12))

    sl = load_slice()
    step_data(sl)
    step_null_bug(sl, plt)
    step_rate_bug(sl, cfg, seeds, plt)
    step_probe_bug(sl, cfg, seeds, plt)
    step_result(plt)
    print(f"\nfigures written to {FIG_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
