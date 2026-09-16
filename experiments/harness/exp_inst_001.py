"""EXP-INST-001: instrument validation at the E1 measurement config.

Question: at 48 probes / target_rate 0.002 / signed / 12 seeds x 60 trials/class,
can this measurement procedure detect a constructed accuracy effect of ~0.15?

Not a topology test. PASS and FAIL are both valid. Does not reopen EXP-006.
Stock PC-B (ring vs ER, all-excitatory, unknown effect size) is not this experiment;
see experiments/results/EXP-INST-001/protocol.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import e1_reservoir as H
import positive_control as PC
from flylab.dynamics import LIFParams, post_pre_from_pre_post
from flylab.graph import load_graph, induced_subgraph
from flylab.spectral import spectral_radius, syn_scale_for_gain, gain_for_target_rate

OUT_DIR = ROOT / "experiments/results/EXP-INST-001"
N_PROBES = 48
TARGET_RATE = 0.002
N_SEEDS = 12
SEEDS = list(range(N_SEEDS))
N_TRIALS = 60
N_BINS = 4
TARGET_EFFECT = 0.15
MIN_EFFECT = PC.MIN_EFFECT  # 0.10; do not weaken
INJECTION_STREAM = 77_001
NULL_PERM_STREAM = 88_001
CAL_STREAM = 76_001
N_NULL_PERMS = 20
QUIESCENT_GAIN = 0.3
IGNITED_GAIN = 12.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_json(path: Path, obj) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=_json_default))
    tmp.replace(path)
    return path


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not jsonable: {type(o)}")


def git_rev() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def env_info() -> dict:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "numpy": np.__version__,
        "nproc": os.cpu_count(),
        "cwd": os.getcwd(),
        "git_rev": git_rev(),
        "git_branch": subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip(),
        "utc": utc_now(),
    }


def dataset_hashes() -> dict:
    gdir = ROOT / "data/derived/graph"
    lock = ROOT / "data/manifests/source.lock.json"
    files = {
        "source.lock.json": lock,
        "graph_meta.json": gdir / "graph_meta.json",
        "csr_unsigned.npz": gdir / "csr_unsigned.npz",
        "csc_unsigned.npz": gdir / "csc_unsigned.npz",
        "coo_signed.npz": gdir / "coo_signed.npz",
    }
    out = {}
    for k, p in files.items():
        out[k] = {
            "path": str(p),
            "exists": p.exists(),
            "sha256": sha256_file(p) if p.exists() else None,
            "bytes": p.stat().st_size if p.exists() else None,
        }
    return out


def split_indices(y: np.ndarray):
    """E1 temporal hold-out: within each class, first 70% train, last 30% test."""
    tr, te = [], []
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        cut = int(0.7 * len(idx))
        tr.extend(idx[:cut].tolist())
        te.extend(idx[cut:].tolist())
    return np.array(tr, dtype=np.int64), np.array(te, dtype=np.int64)


def class_templates(n_features: int, n_classes: int, rng: np.random.Generator) -> np.ndarray:
    """Orthonormal class templates in feature space. Independent of any reservoir draw."""
    G = rng.normal(size=(n_features, n_classes))
    Q, _ = np.linalg.qr(G)
    return Q.T.copy()  # (K, D)


def inject(X, y, templates, amplitude: float, sigma: float) -> np.ndarray:
    return np.asarray(X, dtype=np.float64) + (amplitude * sigma) * templates[np.asarray(y)]


def train_sigma(X, tr) -> float:
    sl = np.asarray(X, dtype=np.float64)[tr]
    s = float(sl.std(axis=0, ddof=1).mean()) if sl.shape[0] > 1 else 0.0
    return s if s > 1e-12 else 1e-12


def theory_sigma(target_rate: float = TARGET_RATE, n_steps: int = 64,
                 n_bins: int = N_BINS) -> float:
    """Bernoulli std of a bin-averaged spike indicator at the registered rate.

    Does not use reservoir draws. Using mean per-feature train std instead
    collapses the injection on sparse 48-probe rasters (smoke: Δacc=0).
    """
    bin_len = n_steps / float(n_bins)
    return float(np.sqrt(target_rate * (1.0 - target_rate) / bin_len))


def score_features(X, y, tr, te, n_classes: int, seed: int) -> dict:
    r = H.ridge_sweep(X[tr], y[tr], X[te], y[te], n_classes, seed=seed)
    return {
        "acc": float(r["acc"]),
        "train_acc": float(r["train_acc"]),
        "selected_ridge": float(r["selected_ridge"]),
        "train_test_gap": float(r["train_test_gap"]),
    }


def make_trials_for(cfg, n, seed):
    rng = np.random.default_rng(seed)
    I_list, y, inputs = H.make_trials(n, cfg, rng)
    tr, te = split_indices(y)
    return I_list, y, inputs, tr, te


def match_gain(W, rho, I_match, inputs, cfg, seed, n_pool, target_rate):
    base = cfg["dynamics"]["lif"]

    def rate_fn(gain):
        ss = syn_scale_for_gain(rho, gain, base["tau_m"], base.get("dt", 1.0))
        _, st = H.reservoir_features(
            W, I_match, LIFParams(**{**base, "syn_scale": ss}),
            seed, input_ids=inputs, n_probes=8,
        )
        return st["pool_spikes"] / (len(I_match) * cfg["dynamics"]["n_steps"] * n_pool)

    return gain_for_target_rate(rate_fn, target_rate, lo=0.05, hi=80.0)


def simulate_X(W, rho, gain, I_list, inputs, cfg, seed, n_probes):
    base = cfg["dynamics"]["lif"]
    ss = syn_scale_for_gain(rho, gain, base["tau_m"], base.get("dt", 1.0))
    lif = LIFParams(**{**base, "syn_scale": ss})
    X, st = H.reservoir_features(W, I_list, lif, seed, input_ids=inputs, n_probes=n_probes)
    return X, st, ss


def probes_ok(n, inputs, n_probes) -> bool:
    probes, _ = H.probe_set(n, input_ids=inputs, n_probes=n_probes)
    return len(np.intersect1d(probes, inputs)) == 0


def calibrate_amplitude(templates, n_features, n_classes, n_trials, target=TARGET_EFFECT,
                        n_cal_seeds=12) -> dict:
    """Lock alpha on isotropic Gaussians. Never uses reservoir features or the connectome.

    Synthetic draws are frozen per calibration seed so the amplitude search is a
    monotone SNR sweep on the same noise, not a new random problem at each amp.
    """
    cal_seeds = list(range(n_cal_seeds))
    frozen = []
    for s in cal_seeds:
        rng = np.random.default_rng([CAL_STREAM, s])
        n = n_trials * n_classes
        X = rng.normal(0.0, 1.0, size=(n, n_features))
        y = np.repeat(np.arange(n_classes), n_trials)
        tr, te = split_indices(y)
        y_perm = rng.permutation(y)
        frozen.append((s, X, y, tr, te, y_perm))

    def mean_delta(amp: float) -> float:
        diffs = []
        for s, X, y, tr, te, y_perm in frozen:
            pos = score_features(inject(X, y, templates, amp, 1.0), y, tr, te, n_classes, s)
            nul = score_features(inject(X, y_perm, templates, amp, 1.0), y, tr, te, n_classes, s)
            diffs.append(pos["acc"] - nul["acc"])
        return float(np.mean(diffs))

    d0 = mean_delta(0.0)
    lo, hi = 0.0, 8.0
    d_hi = mean_delta(hi)
    search = [{"amp": 0.0, "mean_delta": d0}, {"amp": hi, "mean_delta": d_hi}]
    if d_hi < target:
        return {
            "ok": False,
            "reason": "synthetic_ceiling_below_target",
            "target": target,
            "delta_at_0": d0,
            "delta_at_hi": d_hi,
            "hi": hi,
            "search": search,
        }
    amp = hi
    for _ in range(16):
        mid = 0.5 * (lo + hi)
        dm = mean_delta(mid)
        search.append({"amp": mid, "mean_delta": dm})
        amp = mid
        if dm >= target:
            hi = mid
        else:
            lo = mid
    locked = float(hi)
    per = []
    for s, X, y, tr, te, y_perm in frozen:
        pos = score_features(inject(X, y, templates, locked, 1.0), y, tr, te, n_classes, s)["acc"]
        nul = score_features(inject(X, y_perm, templates, locked, 1.0), y, tr, te, n_classes, s)["acc"]
        per.append({"seed": s, "acc_pos": pos, "acc_null": nul, "diff": pos - nul})
    diffs = np.array([p["diff"] for p in per], dtype=float)
    return {
        "ok": True,
        "alpha_star": locked,
        "target_effect": target,
        "calibrated_mean_delta": float(diffs.mean()),
        "calibrated_ci95": float(1.96 * diffs.std(ddof=1) / np.sqrt(len(diffs))) if len(diffs) > 1 else 0.0,
        "delta_at_0": d0,
        "n_cal_seeds": n_cal_seeds,
        "n_features": n_features,
        "n_classes": n_classes,
        "n_trials_per_class": n_trials,
        "feature_model": "isotropic_gaussian_N(0,1)",
        "per_seed": per,
        "search": search,
        "note": "alpha_star locked here; not retuned on reservoir data",
    }


def gate_from_pairs(a, b, min_effect=MIN_EFFECT) -> dict:
    return PC.verdict(PC.paired_stats(a, b), min_effect=min_effect)


def svg_per_seed(diffs_pos, diffs_null, path: Path, threshold: float = MIN_EFFECT):
    """Tiny SVG; no matplotlib dependency."""
    w, h, pad = 640, 280, 40
    vals = list(diffs_pos) + list(diffs_null) + [threshold, -threshold, 0.0]
    lo, hi = min(vals) - 0.05, max(vals) + 0.05
    if hi <= lo:
        hi = lo + 1.0

    def yy(v):
        return pad + (h - 2 * pad) * (1.0 - (v - lo) / (hi - lo))

    def xx(i, n, offset):
        return pad + (w - 2 * pad) * ((i + offset) / max(n, 1))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{pad}" x2="{w - pad}" y1="{yy(0)}" y2="{yy(0)}" stroke="#888"/>',
        f'<line x1="{pad}" x2="{w - pad}" y1="{yy(threshold)}" y2="{yy(threshold)}" '
        f'stroke="#c00" stroke-dasharray="4"/>',
        f'<text x="{pad}" y="18" font-size="12" font-family="sans-serif">'
        f"per-seed Δacc (red=positive injection, gray=null perm 0)</text>",
    ]
    n = max(len(diffs_pos), 1)
    for i, d in enumerate(diffs_pos):
        parts.append(
            f'<circle cx="{xx(i, n, 0.35):.1f}" cy="{yy(d):.1f}" r="4" fill="#c0392b"/>'
        )
    for i, d in enumerate(diffs_null):
        parts.append(
            f'<circle cx="{xx(i, n, 0.55):.1f}" cy="{yy(d):.1f}" r="4" fill="#7f8c8d"/>'
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts))
    return path


def prepare_cfg(n_trials: int) -> dict:
    cfg = H.load_cfg()
    cfg["dynamics"]["n_trials_per_class"] = int(n_trials)
    guards = dict(cfg.get("harness_guards", {}))
    guards["on_dead"] = "record"
    cfg["harness_guards"] = guards
    return cfg


def provenance_pre_run(command: list[str]) -> dict:
    script = Path(__file__).resolve()
    cfg_path = HERE / "e1_config.json"
    return {
        "utc": utc_now(),
        "git_rev": git_rev(),
        "command": command,
        "script": str(script),
        "script_sha256": sha256_file(script),
        "e1_config_sha256": sha256_file(cfg_path),
        "positive_control_sha256": sha256_file(HERE / "positive_control.py"),
        "e1_reservoir_sha256": sha256_file(HERE / "e1_reservoir.py"),
        "null_ensemble_sha256": sha256_file(HERE / "null_ensemble.py"),
        "min_effect_gate": MIN_EFFECT,
        "target_effect": TARGET_EFFECT,
        "n_probes": N_PROBES,
        "target_rate": TARGET_RATE,
        "n_seeds": N_SEEDS,
        "seeds": SEEDS,
        "n_trials_per_class": N_TRIALS,
        "dataset": dataset_hashes(),
        "env": env_info(),
        "never_touch": "data/raw/",
        "note": "Recorded before the scientific run. Smoke is not evidence.",
    }


def score_condition(X, y, tr, te, templates, amp, sigma, labels_for_templates, n_classes, seed):
    Xi = inject(X, labels_for_templates, templates, amp, sigma)
    return score_features(Xi, y, tr, te, n_classes, seed)


def analyze_seed(X, y, tr, te, stats, templates, alpha, n_classes, seed, n, n_steps, n_probes,
                 inputs, guards) -> dict:
    n_classes = int(n_classes)
    leak_ok = probes_ok(n, inputs, n_probes)
    liveness = H.check_alive(X, stats, arm="connectome_signed", guards=guards)
    sigma_emp = train_sigma(X, tr)
    sigma = theory_sigma()
    n_pool = n - len(inputs)
    denom = max(len(y) * n_steps * n_pool, 1)
    realised_rate = float(stats["pool_spikes"]) / denom

    rng_null0 = np.random.default_rng([NULL_PERM_STREAM, seed, 0])
    y_perm0 = rng_null0.permutation(y)

    base = score_features(np.asarray(X, dtype=np.float64), y, tr, te, n_classes, seed)
    pos = score_condition(X, y, tr, te, templates, alpha, sigma, y, n_classes, seed)
    nul0 = score_condition(X, y, tr, te, templates, alpha, sigma, y_perm0, n_classes, seed)

    null_perms = []
    acc_nulls = []
    for p in range(N_NULL_PERMS):
        rng_p = np.random.default_rng([NULL_PERM_STREAM, seed, p])
        yp = rng_p.permutation(y)
        sc = score_condition(X, y, tr, te, templates, alpha, sigma, yp, n_classes, seed)
        null_perms.append({"perm": p, "acc": sc["acc"], "selected_ridge": sc["selected_ridge"]})
        acc_nulls.append(sc["acc"])

    # second independent shuffle for a same-energy no-effect pair
    rng_b = np.random.default_rng([NULL_PERM_STREAM, seed, 10_000])
    y_perm_b = rng_b.permutation(y)
    nul_b = score_condition(X, y, tr, te, templates, alpha, sigma, y_perm_b, n_classes, seed)

    return {
        "seed": seed,
        "alive": bool(liveness.get("alive", False)),
        "liveness": liveness,
        "probe_input_leak": (not leak_ok),
        "n_features": int(np.asarray(X).shape[1]),
        "sigma_train": sigma_emp,
        "sigma_theory": sigma,
        "realised_rate": realised_rate,
        "pool_spikes": float(stats["pool_spikes"]),
        "acc_no_injection": base["acc"],
        "acc_positive": pos["acc"],
        "acc_null_perm0": nul0["acc"],
        "acc_null_perm_b": nul_b["acc"],
        "diff_positive_vs_null0": float(pos["acc"] - nul0["acc"]),
        "diff_null_pair": float(nul0["acc"] - nul_b["acc"]),
        "selected_ridge_no_injection": base["selected_ridge"],
        "selected_ridge_positive": pos["selected_ridge"],
        "selected_ridge_null0": nul0["selected_ridge"],
        "null_perm_accs": acc_nulls,
        "null_perms": null_perms,
        "n_train": int(len(tr)),
        "n_test": int(len(te)),
    }


def aggregate(rows: list[dict], alpha: float) -> dict:
    def seed_valid(r):
        return bool(r.get("alive")) and not r.get("liveness", {}).get("dead_reason")

    live = [r for r in rows if seed_valid(r)]
    dead = [r["seed"] for r in rows if not seed_valid(r)]
    leak = [r["seed"] for r in rows if r["probe_input_leak"]]
    use = live
    n_use = len(use)
    power_floor_met = (n_use == N_SEEDS and len(rows) == N_SEEDS
                       and len(leak) == 0)

    def col(key):
        return [r[key] for r in use]

    pos_gate = None
    null_gate = None
    if n_use >= 2:
        pos_gate = gate_from_pairs(col("acc_positive"), col("acc_null_perm0"))
        null_gate = gate_from_pairs(col("acc_null_perm0"), col("acc_null_perm_b"))

    seed_detect_pos = [abs(r["diff_positive_vs_null0"]) >= MIN_EFFECT for r in use]
    seed_detect_null = [abs(r["diff_null_pair"]) >= MIN_EFFECT for r in use]

    # empirical FP: fraction of locked perms whose 12-seed paired test vs perm0 would
    # not apply; instead, for each perm p, paired acc_positive is not used — we test
    # whether perm p vs perm 0 (no true association) passes the gate, and also whether
    # each perm's mean acc vs no-injection looks like a false structure effect.
    fp_perm_gates = []
    if n_use >= 2:
        acc_p0 = col("acc_null_perm0")
        for p in range(1, N_NULL_PERMS):
            acc_p = [r["null_perm_accs"][p] for r in use]
            g = gate_from_pairs(acc_p, acc_p0)
            fp_perm_gates.append({"perm": p, "separated": g["separated"],
                                  "mean_diff": g["mean_diff"], "ci95_diff": g["ci95_diff"]})
    n_fp = sum(1 for g in fp_perm_gates if g["separated"])
    empirical_fp = (n_fp / len(fp_perm_gates)) if fp_perm_gates else None

    diffs_pos = np.array([r["diff_positive_vs_null0"] for r in use], dtype=float) if use else np.array([])
    diffs_null = np.array([r["diff_null_pair"] for r in use], dtype=float) if use else np.array([])

    instrument_valid = bool(
        power_floor_met
        and pos_gate is not None
        and pos_gate["separated"]
    )

    return {
        "n_rows": len(rows),
        "n_live": n_use,
        "dead_seeds": dead,
        "leak_seeds": leak,
        "power_floor_met": power_floor_met,
        "alpha_star": alpha,
        "target_effect": TARGET_EFFECT,
        "min_effect_gate": MIN_EFFECT,
        "positive_vs_null": pos_gate,
        "null_pair": null_gate,
        "mean_acc_no_injection": float(np.mean(col("acc_no_injection"))) if use else None,
        "mean_acc_positive": float(np.mean(col("acc_positive"))) if use else None,
        "mean_acc_null_perm0": float(np.mean(col("acc_null_perm0"))) if use else None,
        "var_diff_positive": float(diffs_pos.var(ddof=1)) if len(diffs_pos) > 1 else None,
        "sd_diff_positive": float(diffs_pos.std(ddof=1)) if len(diffs_pos) > 1 else None,
        "var_diff_null": float(diffs_null.var(ddof=1)) if len(diffs_null) > 1 else None,
        "seed_detection_rate_positive": float(np.mean(seed_detect_pos)) if seed_detect_pos else None,
        "seed_false_detection_rate_null": float(np.mean(seed_detect_null)) if seed_detect_null else None,
        "seed_fn_rate_positive": float(1.0 - np.mean(seed_detect_pos)) if seed_detect_pos else None,
        "empirical_fp_perm_gate": empirical_fp,
        "n_null_perm_gate_tests": len(fp_perm_gates),
        "n_null_perm_gate_pass": n_fp,
        "fp_perm_gates": fp_perm_gates,
        "mean_realised_rate": float(np.mean(col("realised_rate"))) if use else None,
        "INSTRUMENT_VALID_E1": instrument_valid,
        "gate_rule": "all 12 planned seeds pass all liveness guards; no probe leak; "
                     "|mean_diff|>=0.10 and ci_excludes_zero "
                     "on true-label injection vs locked shuffle perm0",
    }


def pc_a_block(W, rho, I_list, y, tr, te, inputs, cfg, seed, n_probes) -> dict:
    Xq, stq, ssq = simulate_X(W, rho, QUIESCENT_GAIN, I_list, inputs, cfg, seed, n_probes)
    Xi, sti, ssi = simulate_X(W, rho, IGNITED_GAIN, I_list, inputs, cfg, seed, n_probes)
    n_classes = cfg["dynamics"]["n_classes"]
    guards = cfg.get("harness_guards", {})
    lq = H.check_alive(Xq, stq, "pc_a_quiescent", guards)
    li = H.check_alive(Xi, sti, "pc_a_ignited", guards)
    q = score_features(np.asarray(Xq, dtype=np.float64), y, tr, te, n_classes, seed)
    i = score_features(np.asarray(Xi, dtype=np.float64), y, tr, te, n_classes, seed)
    return {
        "seed": seed,
        "quiescent": {"gain": QUIESCENT_GAIN, "syn_scale": ssq, "acc": q["acc"],
                      "pool_spikes": stq["pool_spikes"], "alive": lq.get("alive")},
        "ignited": {"gain": IGNITED_GAIN, "syn_scale": ssi, "acc": i["acc"],
                    "pool_spikes": sti["pool_spikes"], "alive": li.get("alive")},
    }


def conclusion_text(agg: dict, pc_a: dict | None) -> dict:
    valid = bool(agg["INSTRUMENT_VALID_E1"])
    if valid:
        interp = (
            "The E1 measurement procedure detected the pre-registered constructed "
            "effect of ~0.15 under the predefined gate (|mean_diff|>=0.10 and 95% CI "
            "excludes 0). INSTRUMENT_VALID_E1=TRUE. This does not evaluate MaleCNS "
            "topology and does not reopen EXP-006. EXP-E1B-001 is not launched here."
        )
        next_step = "STOP. Do not launch EXP-E1B-001 from this runner."
        sensitivity = None
    else:
        interp = (
            "This E1 config lacks sensitivity to detect the predefined effect. "
            "That is an instrument result. It is not evidence that connectome "
            "topology is false, and it is not evidence that Fly does not work. "
            "Do not interpret E1 connectome-vs-null accuracies as a topology test."
        )
        next_step = (
            "STOP. Phase 2 remains blocked. Do not implement sensitivity changes "
            "in this experiment. Do not launch EXP-E1B-001 or EXP-MEM-001."
        )
        sensitivity = [
            "More readout probes (the only passing stock PC used 450, not 48).",
            "Higher non-input firing rate (passing stock PC used 0.01, not 0.002).",
            "Features other than 48 probes x 4 temporal bins.",
            "A signed structural positive control, still at a config that first passes this gate.",
        ]
    return {
        "INSTRUMENT_VALID_E1": valid,
        "verdict": "PASS" if valid else "FAIL",
        "interpretation": interp,
        "next_step": next_step,
        "what_would_raise_sensitivity": sensitivity,
        "pc_a_separated": None if pc_a is None else pc_a.get("separated"),
        "language_forbidden": [
            "breakthrough", "proves", "superiority", "inferiority",
            "topology is false", "Fly does not work",
        ],
    }


def write_readme(agg: dict, conc: dict, smoke: dict, paths: dict) -> None:
    pos = agg.get("positive_vs_null") or {}
    lines = [
        "# EXP-INST-001",
        "",
        "Instrument validation at the E1 measurement config "
        "(48 probes / rate 0.002 / signed / 12 x 60).",
        "",
        f"**Verdict:** {conc['verdict']}",
        f"**INSTRUMENT_VALID_E1:** {conc['INSTRUMENT_VALID_E1']}",
        "",
        "## Gate",
        "",
        f"- target constructed effect: {TARGET_EFFECT}",
        f"- predefined MIN_EFFECT: {MIN_EFFECT}",
        f"- mean_diff: {pos.get('mean_diff')}",
        f"- ci95_diff: {pos.get('ci95_diff')}",
        f"- ci_excludes_zero: {pos.get('ci_excludes_zero')}",
        f"- separated: {pos.get('separated')}",
        f"- live seeds: {agg.get('n_live')} / {agg.get('n_rows')}",
        f"- empirical FP (null-perm gates): {agg.get('empirical_fp_perm_gate')}",
        f"- seed detection rate (positive): {agg.get('seed_detection_rate_positive')}",
        f"- seed FN rate (positive): {agg.get('seed_fn_rate_positive')}",
        "",
        "## Interpretation",
        "",
        conc["interpretation"],
        "",
        "## Next step",
        "",
        conc["next_step"],
        "",
        "Smoke is not evidence.",
        f"Smoke status: {smoke.get('status')}",
        "",
        "See protocol.md, summary.json, stats.json, conclusion.json.",
    ]
    Path(paths["readme"]).write_text("\n".join(lines) + "\n")


def run_smoke_synthetic(templates, n_features, n_classes) -> dict:
    """Schema / estimator / gate / injection plumbing. Not evidence."""
    rng = np.random.default_rng(12345)
    n_trials = 12
    n = n_trials * n_classes
    X = rng.normal(0, 1, size=(n, n_features))
    y = np.repeat(np.arange(n_classes), n_trials)
    tr, te = split_indices(y)
    assert set(tr).isdisjoint(set(te)), "split leakage"
    y_perm = np.random.default_rng(999).permutation(y)
    assert not np.array_equal(y_perm, y) or n_classes == 1
    pos = score_features(inject(X, y, templates, 2.0, 1.0), y, tr, te, n_classes, 0)
    nul = score_features(inject(X, y_perm, templates, 2.0, 1.0), y, tr, te, n_classes, 0)
    g_pos = gate_from_pairs([pos["acc"], pos["acc"] + 0.2], [nul["acc"], nul["acc"]])
    g_tiny = gate_from_pairs([0.51] * 6, [0.50] * 6)
    return {
        "status": "ok",
        "n_train": int(len(tr)),
        "n_test": int(len(te)),
        "split_disjoint": True,
        "acc_pos_amp2": pos["acc"],
        "acc_null_amp2": nul["acc"],
        "gate_tiny_separated": g_tiny["separated"],
        "estimator": "ridge_sweep",
        "note": "smoke_synthetic_not_evidence",
        "gate_fn_imported_min_effect": MIN_EFFECT,
        "dummy_gate_keys": sorted(g_pos.keys()),
    }


def run_smoke_real(W, rho, cfg, templates, alpha, n_probes, target_rate) -> dict:
    t0 = time.time()
    smoke_cfg = json.loads(json.dumps(cfg))
    smoke_cfg["dynamics"]["n_trials_per_class"] = 8
    n = W.shape[0]
    I_list, y, inputs, tr, te = make_trials_for(smoke_cfg, n, seed=0)
    n_pool = n - len(inputs)
    stride = max(1, len(I_list) // 8)
    I_match = I_list[::stride]
    matched = match_gain(W, rho, I_match, inputs, smoke_cfg, 0, n_pool, target_rate)
    X, st, ss = simulate_X(W, rho, matched["gain"], I_list, inputs, smoke_cfg, 0, n_probes)
    row = analyze_seed(
        X, y, tr, te, st, templates, alpha, smoke_cfg["dynamics"]["n_classes"],
        0, n, smoke_cfg["dynamics"]["n_steps"], n_probes, inputs,
        smoke_cfg.get("harness_guards", {}),
    )
    dt = time.time() - t0
    n_full_trials = N_TRIALS * cfg["dynamics"]["n_classes"]
    n_smoke_trials = 8 * smoke_cfg["dynamics"]["n_classes"]
    # 12 full seeds of features + 12 PC-A * 2 gains; scale from 1 seed x 8 trials
    est_s = dt * (N_SEEDS * (1 + 2) * (n_full_trials / max(n_smoke_trials, 1)))
    return {
        "status": "ok",
        "seconds": dt,
        "estimated_full_seconds": est_s,
        "matched_gain": matched,
        "syn_scale": ss,
        "row": {k: v for k, v in row.items() if k != "null_perms"},
        "note": "smoke_real_not_evidence",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="EXP-INST-001 instrument validation")
    ap.add_argument("--smoke-only", action="store_true")
    ap.add_argument("--skip-smoke", action="store_true")
    ap.add_argument("--skip-pc-a", action="store_true",
                    help="diagnostic only; full protocol runs PC-A")
    ap.add_argument("--max-estimated-seconds", type=float, default=900.0)
    args = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_dir = OUT_DIR / "raw"
    raw_dir.mkdir(exist_ok=True)

    command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
    prov = provenance_pre_run(command)
    write_json(OUT_DIR / "provenance.json", prov)
    write_json(OUT_DIR / "env.json", prov["env"])
    write_json(OUT_DIR / "seeds.json", {
        "task_seeds": SEEDS,
        "injection_stream": INJECTION_STREAM,
        "null_perm_stream": NULL_PERM_STREAM,
        "calibration_stream": CAL_STREAM,
        "disjoint_from_null_ensemble_stream": 90_000,
    })

    n_classes = 5
    n_features = N_PROBES * N_BINS
    rng_t = np.random.default_rng(INJECTION_STREAM)
    templates = class_templates(n_features, n_classes, rng_t)
    write_json(OUT_DIR / "templates.json", {
        "shape": list(templates.shape),
        "stream": INJECTION_STREAM,
        "templates": templates.tolist(),
    })

    print("calibrating alpha_star on Gaussians (not reservoir)...", flush=True)
    cal = calibrate_amplitude(templates, n_features, n_classes, N_TRIALS, TARGET_EFFECT)
    write_json(OUT_DIR / "calibration.json", cal)
    if not cal["ok"]:
        write_json(OUT_DIR / "conclusion.json", {
            "INSTRUMENT_VALID_E1": False,
            "verdict": "STOP",
            "classification": "stats",
            "reason": cal.get("reason"),
        })
        print("STOP: calibration could not lock a 0.15 synthetic effect", flush=True)
        return 3
    alpha = float(cal["alpha_star"])
    print(f"  locked alpha_star={alpha:.4f} synthetic_delta={cal['calibrated_mean_delta']:.4f}",
          flush=True)

    smoke = {"status": "skipped"}
    smoke["synthetic"] = run_smoke_synthetic(templates, n_features, n_classes)
    write_json(OUT_DIR / "smoke_synthetic.json", smoke["synthetic"])

    cfg = prepare_cfg(N_TRIALS)
    print("loading graph...", flush=True)
    t_load = time.time()
    g = load_graph(load_neurons=False)
    nodes = H.select_nodes(g, cfg["subgraph"]["n"])
    A, nodes = induced_subgraph(g, nodes)
    W = post_pre_from_pre_post(A)
    n, nnz = A.shape[0], int(W.nnz)
    rho = spectral_radius(W)
    print(f"  n={n} nnz={nnz} rho={rho:.4f} load+spectrum {time.time()-t_load:.1f}s", flush=True)

    if not args.skip_smoke:
        print("real smoke (8 trials/class, seed 0)...", flush=True)
        smoke["real"] = run_smoke_real(W, rho, cfg, templates, alpha, N_PROBES, TARGET_RATE)
        write_json(OUT_DIR / "smoke_real.json", smoke["real"])
        est = float(smoke["real"]["estimated_full_seconds"])
        print(f"  smoke {smoke['real']['seconds']:.1f}s; estimated full ~{est:.0f}s", flush=True)
        if est > args.max_estimated_seconds:
            write_json(OUT_DIR / "conclusion.json", {
                "INSTRUMENT_VALID_E1": False,
                "verdict": "STOP",
                "classification": "compute",
                "estimated_full_seconds": est,
                "max_estimated_seconds": args.max_estimated_seconds,
                "note": "Did not shrink the science. Stopped before the full run.",
            })
            print("STOP: estimated runtime exceeds budget; science not shrunk", flush=True)
            return 4
        smoke["status"] = "ok"

    if args.smoke_only:
        write_json(OUT_DIR / "conclusion.json", {
            "INSTRUMENT_VALID_E1": None,
            "verdict": "SMOKE_ONLY",
            "note": "smoke is not evidence",
        })
        print("smoke-only done", flush=True)
        return 0

    # Gain match once on seed 0 — E1 measurement config.
    I0, y0, in0, tr0, te0 = make_trials_for(cfg, n, SEEDS[0])
    n_pool = n - len(in0)
    stride = max(1, len(I0) // 20)
    I_match = I0[::stride]
    print("matching gain on seed 0 (E1 config)...", flush=True)
    matched = match_gain(W, rho, I_match, in0, cfg, SEEDS[0], n_pool, TARGET_RATE)
    write_json(OUT_DIR / "gain_match.json", {"seed": SEEDS[0], **matched, "rho": rho})
    print(f"  gain={matched['gain']:.4f} converged={matched['converged']} "
          f"rate={matched.get('rate')}", flush=True)

    rows = []
    pc_a_rows = []
    t_run = time.time()
    n_classes = cfg["dynamics"]["n_classes"]
    n_steps = cfg["dynamics"]["n_steps"]
    guards = cfg.get("harness_guards", {})

    for seed in SEEDS:
        I_list, y, inputs, tr, te = make_trials_for(cfg, n, seed)
        X, st, ss = simulate_X(W, rho, matched["gain"], I_list, inputs, cfg, seed, N_PROBES)
        row = analyze_seed(
            X, y, tr, te, st, templates, alpha, n_classes, seed, n, n_steps,
            N_PROBES, inputs, guards,
        )
        row["syn_scale"] = ss
        row["gain"] = matched["gain"]
        rows.append(row)
        write_json(raw_dir / f"seed_{seed:02d}.json", row)

        if not args.skip_pc_a:
            pca = pc_a_block(W, rho, I_list, y, tr, te, inputs, cfg, seed, N_PROBES)
            pc_a_rows.append(pca)
            write_json(raw_dir / f"pc_a_seed_{seed:02d}.json", pca)

        partial = aggregate(rows, alpha)
        write_json(OUT_DIR / "summary_partial.json", {
            "utc": utc_now(),
            "completed_seeds": [r["seed"] for r in rows],
            "aggregate": {k: v for k, v in partial.items() if k != "fp_perm_gates"},
        })
        print(f"  seed {seed} alive={row['alive']} acc0={row['acc_no_injection']:.3f} "
              f"pos={row['acc_positive']:.3f} nul={row['acc_null_perm0']:.3f} "
              f"d={row['diff_positive_vs_null0']:.3f} rate={row['realised_rate']:.5f} "
              f"t={time.time()-t_run:.1f}s", flush=True)

    agg = aggregate(rows, alpha)
    pc_a_stats = None
    if pc_a_rows:
        pc_a_stats = gate_from_pairs(
            [r["ignited"]["acc"] for r in pc_a_rows],
            [r["quiescent"]["acc"] for r in pc_a_rows],
        )
        pc_a_stats["detail"] = pc_a_rows

    conc = conclusion_text(agg, pc_a_stats)
    stats = {
        "positive_vs_null": agg.get("positive_vs_null"),
        "null_pair": agg.get("null_pair"),
        "empirical_fp_perm_gate": agg.get("empirical_fp_perm_gate"),
        "seed_detection_rate_positive": agg.get("seed_detection_rate_positive"),
        "seed_fn_rate_positive": agg.get("seed_fn_rate_positive"),
        "seed_false_detection_rate_null": agg.get("seed_false_detection_rate_null"),
        "var_diff_positive": agg.get("var_diff_positive"),
        "sd_diff_positive": agg.get("sd_diff_positive"),
        "mean_realised_rate": agg.get("mean_realised_rate"),
        "mean_acc_no_injection": agg.get("mean_acc_no_injection"),
        "mean_acc_positive": agg.get("mean_acc_positive"),
        "mean_acc_null_perm0": agg.get("mean_acc_null_perm0"),
        "pc_a": {k: v for k, v in (pc_a_stats or {}).items() if k != "detail"},
        "calibration": {
            "alpha_star": alpha,
            "synthetic_mean_delta": cal["calibrated_mean_delta"],
            "target_effect": TARGET_EFFECT,
        },
        "seconds": time.time() - t_run,
    }

    summary = {
        "experiment_id": "EXP-INST-001",
        "provenance": {**prov, "run_utc": utc_now()},
        "n": n,
        "nnz": nnz,
        "rho_signed": rho,
        "n_probes": N_PROBES,
        "target_rate": TARGET_RATE,
        "n_trials_per_class": N_TRIALS,
        "seeds": SEEDS,
        "gain_match": matched,
        "calibration": cal,
        "rows": rows,
        "aggregate": agg,
        "pc_a": pc_a_stats,
        "seconds": time.time() - t_run,
        "INSTRUMENT_VALID_E1": conc["INSTRUMENT_VALID_E1"],
        "verdict": conc["verdict"],
    }
    write_json(OUT_DIR / "summary.json", summary)
    write_json(OUT_DIR / "stats.json", stats)
    write_json(OUT_DIR / "conclusion.json", conc)
    write_json(OUT_DIR / "raw_results.json", {"rows": rows, "pc_a": pc_a_rows})

    diffs_pos = [r["diff_positive_vs_null0"] for r in rows if r["alive"]]
    diffs_null = [r["diff_null_pair"] for r in rows if r["alive"]]
    try:
        svg_per_seed(diffs_pos, diffs_null, OUT_DIR / "per_seed_diff.svg")
    except Exception as exc:
        print("plot skipped:", exc, flush=True)

    write_readme(agg, conc, smoke, {"readme": OUT_DIR / "README.md"})
    # never-overwrite copy in the versioned results dir
    stamped = H.write_result(summary, prefix="exp_inst_001")
    print("GATE:", conc["verdict"], "INSTRUMENT_VALID_E1=", conc["INSTRUMENT_VALID_E1"],
          flush=True)
    print("WROTE", OUT_DIR, "and", stamped, flush=True)
    return 0 if conc["INSTRUMENT_VALID_E1"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
