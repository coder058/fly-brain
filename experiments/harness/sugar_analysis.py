"""EXP-W1-SUGAR analysis: the preregistered endpoints, computed from the committed result files.

Reads the latest complete `sugar_<label>_*.json` for each run (malecns-both, malecns-lateral,
flywire) and the post-hoc file, applies the decision rules of protocol.md, and writes
`analysis.json` next to them. Prints a summary for the report.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "experiments/results/EXP-W1-SUGAR"
LOGGED_FIRST_RUN = {0: 0.0, 50: 51.7, 100: 72.2, 150: 83.6, 200: 95.4}  # protocol execution note


def latest(label: str, directory: Path = RESULTS) -> dict | None:
    done = [json.loads(p.read_text()) for p in sorted(directory.glob(f"sugar_{label}_*.json"))]
    done = [r for r in done if r.get("complete", True)]
    return done[-1] if done else None


def t_ci(x) -> tuple[float, float, float]:
    x = np.asarray(x, dtype=float)
    m = float(x.mean())
    if x.std() == 0:
        return m, m, m
    h = float(stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)))
    return m, m - h, m + h


def curve(res: dict, inp: str) -> list[dict]:
    return sorted((c for c in res["conditions"].values()
                   if c["input"] == inp and "null_draw" not in c), key=lambda c: c["rate_hz"])


def primary(mc: dict) -> dict:
    top = curve(mc, "lb3c_both")[-1]
    zero = curve(mc, "lb3c_both")[0]
    assert top["rate_hz"] == 200 and zero["rate_hz"] == 0
    m, lo, hi = t_ci(top["mn9_trials"])
    zero_mean = float(np.mean(zero["mn9_trials"]))
    verdict = ("replicates" if lo > 10 and zero_mean < 2 else
               "does not replicate" if hi < 10 else "inconclusive")
    return {"mn9_mean": m, "ci95": [lo, hi], "zero_hz_mean": zero_mean, "verdict": verdict}


def dose_response(res: dict, inp: str) -> dict:
    pts = curve(res, inp)
    rho, p = stats.spearmanr([c["rate_hz"] for c in pts], [c["mn9_mean"] for c in pts])
    return {"rates": [c["rate_hz"] for c in pts], "mn9": [c["mn9_mean"] for c in pts],
            "mn9_each": [c.get("mn9_each") for c in pts],
            "active": [c["active_neurons"] for c in pts], "spearman": float(rho), "p": float(p)}


def overlap(fw: dict, mc: dict, k: int = 30) -> dict:
    ft = curve(fw, "lb3c_both")[-1]["type_rates"]
    mt = curve(mc, "lb3c_both")[-1]["type_rates"]
    top = sorted(ft, key=ft.get, reverse=True)[:k]
    hits = [t for t in top if mt.get(t, 0.0) > 1.0]
    shared = [t for t in ft if t in mt and (ft[t] > 0 or mt[t] > 0)]
    rho, p = stats.spearmanr([ft[t] for t in shared], [mt[t] for t in shared])
    return {"top_k": k, "flywire_top": [[t, ft[t], mt.get(t)] for t in top],
            "hits": hits, "n_hits": len(hits), "top_absent_in_malecns": [t for t in top if t not in mt],
            "n_shared_active": len(shared), "spearman": float(rho), "p": float(p)}


def overlap_by_flywire_type(fw: dict, mc: dict, k: int = 30) -> dict:
    """POST HOC (not preregistered). The preregistered overlap matches type *names*, but most
    FlyWire types in the gustatory zone are named CB0xxx while MaleCNS names the same cells
    GNGxxx and records the correspondence in `flywireType`. Here each FlyWire type gets the
    neuron-weighted mean rate of the MaleCNS types annotated with it."""
    import pyarrow.feather as feather

    ft = curve(fw, "lb3c_both")[-1]["type_rates"]
    mt = curve(mc, "lb3c_both")[-1]["type_rates"]
    n = feather.read_table(ROOT / "data/derived/graph/neurons.feather",
                           columns=["type", "flywireType"]).to_pandas().dropna()
    acc: dict[str, list[float]] = {}
    for (fwt, t), cnt in n.groupby(["flywireType", "type"]).size().items():
        if t in mt:
            for x in str(fwt).split(","):
                a = acc.setdefault(x.strip(), [0.0, 0])
                a[0] += mt[t] * cnt
                a[1] += cnt
    mapped = {key: a[0] / a[1] for key, a in acc.items() if a[1]}
    top = sorted(ft, key=ft.get, reverse=True)[:k]
    shared = [t for t in ft if t in mapped and (ft[t] > 0 or mapped[t] > 0)]
    rho, p = stats.spearmanr([ft[t] for t in shared], [mapped[t] for t in shared])
    return {"preregistered": False, "top_k": k,
            "flywire_top": [[t, ft[t], mapped.get(t)] for t in top],
            "n_mapped": sum(t in mapped for t in top),
            "n_hits": sum(mapped.get(t, 0.0) > 1.0 for t in top),
            "n_shared_active": len(shared), "spearman": float(rho), "p": float(p)}


def nulls(mc: dict) -> dict:
    draws = [c for c in mc["conditions"].values() if "null_draw" in c]
    _, lo, _ = t_ci(curve(mc, "lb3c_both")[-1]["mn9_trials"])
    means = [c["mn9_mean"] for c in draws]
    return {"null_means": means, "null_active": [c["active_neurons"] for c in draws],
            "connectome_ci_low": lo,
            "pathway_depends_on_wiring": bool(draws) and all(m < lo for m in means)}


def rerun_check(mc: dict) -> dict:
    got = {int(c["rate_hz"]): round(c["mn9_mean"], 1) for c in curve(mc, "lb3c_both")}
    return {"logged": LOGGED_FIRST_RUN, "rerun": got,
            "identical": all(got.get(r) == v for r, v in LOGGED_FIRST_RUN.items())}


def analyse_calib(directory: Path = ROOT / "experiments/results/EXP-W2-CALIB") -> dict | None:
    """EXP-W2-CALIB endpoints (protocol in that directory)."""
    runs = [json.loads(p.read_text()) for p in sorted(directory.glob("calib_*.json"))]
    runs = [r for r in runs if r.get("complete")]
    fw = latest("flywire")
    if not runs or fw is None:
        return None
    cal = runs[-1]
    top = curve(cal, "lb3c_both")[-1]
    out = {"experiment": "EXP-W2-CALIB", "scale": cal["calibration"]["scale"],
           "flywire_reference_active_per_trial": cal["flywire_reference_active_per_trial"],
           "calibration": cal["calibration"]["history"],
           "primary": primary(cal) | {"verdict": None},
           "dose_response": dose_response(cal, "lb3c_both"), "nulls": nulls(cal),
           "spread_200hz": {"active_any_trial": top["active_neurons"],
                            "active_per_trial": top["active_per_trial"]},
           "overlap_by_flywire_type": overlap_by_flywire_type(fw, cal)}
    p = out["primary"]
    lo, hi = p["ci95"]
    p["verdict"] = ("survives calibration" if lo > 10 and p["zero_hz_mean"] < 2 else
                    "does not survive" if hi < 10 else "inconclusive")
    (directory / "analysis.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, default=RESULTS)
    args = ap.parse_args(argv)
    mc, lat, fw = (latest(x, args.dir) for x in ("malecns-both", "malecns-lateral", "flywire"))
    if mc is None:
        print("no complete malecns-both result yet", file=sys.stderr)
        return 1
    out = {"experiment": "EXP-W1-SUGAR", "rerun_check": rerun_check(mc), "primary": primary(mc),
           "dose_response_malecns": dose_response(mc, "lb3c_both"), "nulls": nulls(mc)}
    if lat is not None:
        out["laterality"] = {inp: dose_response(lat, inp) for inp in ("lb3c_L", "lb3c_R")}
    if fw is not None:
        out["flywire"] = {inp: dose_response(fw, inp) for inp in ("lb3c_both", "shiu21")
                          if curve(fw, inp)}
        out["overlap"] = overlap(fw, mc)
        if (ROOT / "data/derived/graph/neurons.feather").exists():
            out["overlap_by_flywire_type_posthoc"] = overlap_by_flywire_type(fw, mc)
    posthoc = sorted(args.dir.glob("sugar_posthoc_*.json"))
    if posthoc:
        out["posthoc"] = [{k: r[k] for k in ("label", "connectome", "mn9_mean", "mn9_each",
                                             "active_neurons", "w_syn")}
                          for r in json.loads(posthoc[-1].read_text())["rows"]]
    (args.dir / "analysis.json").write_text(json.dumps(out, indent=1) + "\n")

    p = out["primary"]
    print(f"rerun identical to logged first run: {out['rerun_check']['identical']} "
          f"({out['rerun_check']['rerun']})")
    print(f"PRIMARY MaleCNS lb3c_both @200 Hz: MN9 {p['mn9_mean']:.1f} Hz "
          f"[{p['ci95'][0]:.1f}, {p['ci95'][1]:.1f}], 0 Hz {p['zero_hz_mean']:.1f} -> {p['verdict']}")
    d = out["dose_response_malecns"]
    print(f"dose response Spearman {d['spearman']:.2f}; active {d['active']}")
    n = out["nulls"]
    print(f"nulls {n['null_means']} vs CI low {n['connectome_ci_low']:.1f} -> "
          f"depends on wiring: {n['pathway_depends_on_wiring']}")
    for inp, r in out.get("laterality", {}).items():
        each = [None if e is None else [round(x, 1) for x in e] for e in r["mn9_each"]]
        print(f"{inp}: MN9 {np.round(r['mn9'], 1).tolist()} (L,R per rate {each})")
    for inp, r in out.get("flywire", {}).items():
        print(f"FlyWire {inp}: MN9 {np.round(r['mn9'], 1).tolist()} active {r['active']}")
    if "overlap" in out:
        o = out["overlap"]
        print(f"overlap: {o['n_hits']}/{o['top_k']} FlyWire top types active >1 Hz in MaleCNS; "
              f"absent {o['top_absent_in_malecns']}; Spearman over {o['n_shared_active']} "
              f"shared types {o['spearman']:.2f}")
    if "overlap_by_flywire_type_posthoc" in out:
        o = out["overlap_by_flywire_type_posthoc"]
        print(f"POST HOC overlap via flywireType: {o['n_hits']}/{o['top_k']} active >1 Hz "
              f"({o['n_mapped']} mapped); Spearman over {o['n_shared_active']} types {o['spearman']:.2f}")
    for r in out.get("posthoc", []):
        print(f"post hoc {r['connectome']} {r['label']}: MN9 {r['mn9_mean']:.1f} active {r['active_neurons']}")
    cal = analyse_calib() if args.dir == RESULTS else None
    if cal:
        p, o = cal["primary"], cal["overlap_by_flywire_type"]
        print(f"EXP-W2-CALIB s={cal['scale']:.4f}: MN9 {p['mn9_mean']:.1f} [{p['ci95'][0]:.1f}, "
              f"{p['ci95'][1]:.1f}], 0 Hz {p['zero_hz_mean']:.1f} -> {p['verdict']}; dose "
              f"{np.round(cal['dose_response']['mn9'], 1).tolist()} rho {cal['dose_response']['spearman']:.2f}; "
              f"nulls {cal['nulls']['null_means']} (wiring: {cal['nulls']['pathway_depends_on_wiring']}); "
              f"spread {cal['spread_200hz']}; overlap {o['n_hits']}/{o['top_k']}, rho {o['spearman']:.2f} "
              f"over {o['n_shared_active']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
