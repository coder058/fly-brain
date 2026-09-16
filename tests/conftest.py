import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments/harness"))


@pytest.fixture(scope="session")
def toy_graph():
    """Small directed signed graph with a defined degree sequence and no self-loops."""
    rng = np.random.default_rng(7)
    n, m = 60, 400
    src = rng.integers(0, n, size=m * 3)
    dst = rng.integers(0, n, size=m * 3)
    keep = src != dst
    src, dst = src[keep], dst[keep]
    pairs = np.unique(np.stack([src, dst], 1), axis=0)[:m]
    src, dst = pairs[:, 0].astype(np.int64), pairs[:, 1].astype(np.int64)
    w = rng.choice([-1.0, 1.0], size=len(src)).astype(np.float32) * rng.uniform(
        1.0, 9.0, size=len(src)
    ).astype(np.float32)
    return n, src, dst, w


@pytest.fixture(scope="session")
def toy_csr(toy_graph):
    n, src, dst, w = toy_graph
    return sparse.csr_matrix((w, (dst, src)), shape=(n, n))  # post x pre
