"""python -m anomaly -- demo one-window score (not a scientific claim)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np

def main(argv=None):
    ap = argparse.ArgumentParser(description="Fly anomaly detector V1 (synthetic / GenericSensorAdapter).")
    ap.add_argument("--npy", help="path to (T,C) float32 npy; if omitted, generate a normal sine window")
    args = ap.parse_args(argv)
    from anomaly.adapters.base import GenericSensorAdapter
    from anomaly.signals import make_dataset
    if args.npy:
        x = np.load(args.npy).astype(np.float32)
        if x.ndim == 1:
            x = x[:, None]
    else:
        X, y = make_dataset(n_normal=1, n_anom=0, T=48, seed=0, shuffle=False)
        x = X[0]
    x = GenericSensorAdapter().to_window(x)
    # cheap statistical score vs a tiny normal bank (no MaleCNS load — use for smoke)
    bank, _ = make_dataset(n_normal=32, n_anom=0, T=x.shape[0], n_channels=x.shape[1], seed=0, shuffle=False)
    mu = bank.reshape(len(bank), -1).mean(0)
    sd = bank.reshape(len(bank), -1).std(0) + 1e-6
    score = float(np.abs((x.reshape(-1) - mu) / sd).max())
    print(json.dumps({"score": score, "T": int(x.shape[0]), "C": int(x.shape[1]), "note": "threshold baseline smoke; Fly reservoir via experiments/"}))

if __name__ == "__main__":
    main()
