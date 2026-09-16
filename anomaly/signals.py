"""Synthetic temporal signals: normal / noisy / rare / subtle anomalies."""
from __future__ import annotations
import numpy as np

def make_dataset(
    n_normal: int = 200,
    n_anom: int = 40,
    T: int = 64,
    n_channels: int = 8,
    seed: int = 0,
    anom_kind: str = "spike",
    noise: float = 0.1,
    anom_strength: float = 1.0,
    shuffle: bool = True,
):
    """anom_strength scales anomaly magnitude (1.0 = EXP-001 easy; ~0.25–0.4 = subtle)."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 4 * np.pi, T, dtype=np.float32)
    base = np.stack([np.sin(t * (1 + 0.07 * c) + 0.3 * c) for c in range(n_channels)], axis=1)
    s = float(anom_strength)

    X, y = [], []
    for _ in range(n_normal):
        x = base + rng.normal(0, noise, size=base.shape).astype(np.float32)
        X.append(x); y.append(0)
    for _ in range(n_anom):
        x = base + rng.normal(0, noise, size=base.shape).astype(np.float32)
        if anom_kind == "spike":
            i = rng.integers(T // 4, 3 * T // 4)
            x[i : i + 3] += rng.uniform(2.5, 4.0) * s
        elif anom_kind == "shift":
            x += rng.uniform(1.2, 2.0) * s
        elif anom_kind == "freq":
            x *= (1.0 + 0.8 * s * np.sin(3 * t)[:, None])
        elif anom_kind == "drift":
            # slow ramp — harder for pointwise threshold
            ramp = (np.linspace(0, 1, T, dtype=np.float32) ** 2)[:, None]
            x += ramp * rng.uniform(0.8, 1.4) * s
        elif anom_kind == "local_glitch":
            i = rng.integers(0, T - 2)
            ch = rng.integers(0, n_channels)
            x[i : i + 2, ch] += rng.uniform(1.5, 2.5) * s
        else:
            x[rng.integers(0, T)] += 5.0 * s
        X.append(x); y.append(1)
    X = np.stack(X).astype(np.float32)
    y = np.asarray(y, dtype=np.int64)
    if not shuffle:
        return X, y
    idx = rng.permutation(len(y))
    return X[idx], y[idx]
