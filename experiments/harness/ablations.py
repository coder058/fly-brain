"""PROTOCOL ablations: |w|, weight-permutation, top-k hub removal.

Do not run while null_ensemble.py owns the CPU. This module only constructs
the graphs; evaluation belongs to null_ensemble / e1_reservoir at matched rate.
"""
from __future__ import annotations

import numpy as np
from scipy import sparse

from flylab.nulls import remove_topk_hubs, weight_permutation_null


def connectome_abs(src, dst, weight, n: int) -> sparse.csr_matrix:
    w = np.abs(np.asarray(weight, dtype=np.float32))
    return sparse.csr_matrix((w, (dst, src)), shape=(n, n))


def weight_perm_arm(src, dst, signed_w, n, rng):
    return weight_permutation_null(src, dst, signed_w, n, rng)


def hub_ablation_arm(src, dst, signed_w, n, k: int):
    return remove_topk_hubs(src, dst, signed_w, n, k)
