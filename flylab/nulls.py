"""Null and control graph constructions for E1.

The original `degree_shuffle` permuted the destination array in place and rebuilt a COO
matrix. Because scipy sums duplicate (row, col) entries, collisions silently merged
parallel edges: 7.93% of the 23,708 subgraph edges disappeared and 19 self-loops appeared.
The multiset of in-degrees survives that operation, but the structural degree sequence
(number of distinct neighbours per node) does not, and a degree-preserving null that loses
8% of its edges is a weaker network, not a rewired one.
"""
from __future__ import annotations

import numpy as np
from scipy import sparse


def degree_sequences(src, dst, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Structural out/in degree: distinct neighbours per node, duplicates collapsed."""
    pairs = np.unique(np.stack([np.asarray(src), np.asarray(dst)], axis=1), axis=0)
    return (
        np.bincount(pairs[:, 0], minlength=n),
        np.bincount(pairs[:, 1], minlength=n),
    )


def directed_edge_swap(
    src, dst, n: int, rng: np.random.Generator, n_swaps_per_edge: int = 20
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Degree-preserving directed double-edge swap.

    Picks two edges (a->b), (c->d) and rewires to (a->d), (c->b). Out-degree of a and c and
    in-degree of b and d are unchanged by construction. A swap is rejected if it would make
    a self-loop or duplicate an existing edge, so edge count, both degree sequences and
    simplicity are all exactly preserved.

    Returns (new_src, new_dst, perm) where perm[i] is the original edge whose weight moves to
    new edge i under the legacy convention. Slot i keeps its source and takes edge j's target,
    and perm swaps with the target, so under `perm` a weight follows its *postsynaptic*
    neuron. Slot i itself (identity) is the presynaptic convention.
    """
    src = np.asarray(src, dtype=np.int64).copy()
    dst = np.asarray(dst, dtype=np.int64).copy()
    m = len(src)
    if m < 2:
        return src, dst, np.arange(m)
    perm = np.arange(m)
    present = set(zip(src.tolist(), dst.tolist()))
    target = m * n_swaps_per_edge
    attempts = 0
    accepted = 0
    max_attempts = target * 10
    while accepted < target and attempts < max_attempts:
        attempts += 1
        i, j = rng.integers(0, m, size=2)
        if i == j:
            continue
        a, b = src[i], dst[i]
        c, d = src[j], dst[j]
        if a == d or c == b:
            continue
        if (a, d) in present or (c, b) in present:
            continue
        present.discard((a, b))
        present.discard((c, d))
        present.add((a, d))
        present.add((c, b))
        dst[i], dst[j] = d, b
        perm[i], perm[j] = perm[j], perm[i]
        accepted += 1
    return src, dst, perm


WEIGHTS_FOLLOW = ("post", "pre")


def degree_preserving_null(
    src, dst, signed_w, n: int, rng: np.random.Generator, n_swaps_per_edge: int = 20,
    weights_follow: str = "post",
) -> tuple[sparse.csr_matrix, dict]:
    """Rewired graph with both degree sequences preserved exactly, as a (post, pre) CSR.

    `weights_follow` decides which endpoint keeps its weights through the rewiring:

    - "post" (default; every result before 2026-10-08 used it): each neuron keeps the
      multiset of *incoming* signed weights. Outgoing signs get mixed, so the null breaks
      Dale's law: on the E1 slice 479 of 500 presynaptic neurons end up with both
      excitatory and inhibitory outputs, against 0 in the connectome. The original comment
      here claimed the opposite; see reports/EXP_E1_DALE.md.
    - "pre": each neuron keeps its *outgoing* weights, hence its sign (Dale's law) and
      out-strength; incoming strength is what gets shuffled.
    """
    if weights_follow not in WEIGHTS_FOLLOW:
        raise ValueError(f"weights_follow must be one of {WEIGHTS_FOLLOW}, got {weights_follow!r}")
    src = np.asarray(src, dtype=np.int64)
    dst = np.asarray(dst, dtype=np.int64)
    w = np.asarray(signed_w, dtype=np.float32)
    out0, in0 = degree_sequences(src, dst, n)
    ns, nd, perm = directed_edge_swap(src, dst, n, rng, n_swaps_per_edge)
    if len(w) != len(perm):
        nw = w
    elif weights_follow == "post":
        nw = w[perm]
    else:
        nw = w  # slot i keeps its source and its original weight
    out1, in1 = degree_sequences(ns, nd, n)
    diag = {
        "n_edges_in": int(len(src)),
        "n_edges_out": int(len(ns)),
        "self_loops": int((ns == nd).sum()),
        "duplicate_edges": int(len(ns) - len(np.unique(np.stack([ns, nd], 1), axis=0))),
        "out_degree_preserved": bool(np.array_equal(out0, out1)),
        "in_degree_preserved": bool(np.array_equal(in0, in1)),
        "fraction_edges_rewired": float((dst != nd).mean()),
        "weights_follow": weights_follow,
    }
    if not (diag["out_degree_preserved"] and diag["in_degree_preserved"]):
        raise RuntimeError(f"degree-preserving null did not preserve degrees: {diag}")
    if diag["self_loops"] or diag["duplicate_edges"] or diag["n_edges_out"] != diag["n_edges_in"]:
        raise RuntimeError(f"degree-preserving null is not simple/edge-exact: {diag}")
    A = sparse.csr_matrix((nw, (nd, ns)), shape=(n, n))  # (post, pre)
    return A, diag


def ring_lattice(n: int, nnz: int, rng: np.random.Generator, excitatory_only: bool = True,
                 w_lo: float = 1.0, w_hi: float = 10.0) -> sparse.csr_matrix:
    """Directed ring lattice: i -> i+1 .. i+k (mod n). A delay line, so it has obvious
    temporal memory that a size-matched random graph does not. Used as a positive control:
    if the harness cannot tell this apart from a random graph at matched firing rate, the
    harness has no structural resolving power and nothing it reports about the connectome
    means anything."""
    k = max(1, int(round(nnz / n)))
    src = np.repeat(np.arange(n), k)
    dst = (np.tile(np.arange(1, k + 1), n) + src) % n
    keep = src != dst
    src, dst = src[keep], dst[keep]
    if len(src) > nnz:
        src, dst = src[:nnz], dst[:nnz]
    w = rng.uniform(w_lo, w_hi, size=len(src)).astype(np.float32)
    if not excitatory_only:
        w = w * rng.choice(np.array([-1.0, 1.0], dtype=np.float32), size=len(src))
    return sparse.csr_matrix((w, (dst, src)), shape=(n, n))


def er_graph(n: int, nnz: int, rng: np.random.Generator, excitatory_only: bool = False,
             w_lo: float = 1.0, w_hi: float = 10.0) -> sparse.csr_matrix:
    """Erdos-Renyi digraph with exactly `nnz` distinct edges and no self-loops."""
    max_e = n * (n - 1)
    nnz = min(nnz, max_e)
    flat = rng.choice(max_e, size=nnz, replace=False)
    src = flat // (n - 1)
    dst = flat % (n - 1)
    dst = dst + (dst >= src).astype(np.int64)
    w = rng.uniform(w_lo, w_hi, size=nnz).astype(np.float32)
    if not excitatory_only:
        w = w * rng.choice(np.array([-1.0, 1.0], dtype=np.float32), size=nnz)
    return sparse.csr_matrix((w, (dst, src)), shape=(n, n))


def weight_permutation_null(
    src, dst, signed_w, n: int, rng: np.random.Generator
) -> tuple[sparse.csr_matrix, dict]:
    """PROTOCOL ablation: shuffle weights, keep topology (src, dst) exactly.

    Degree sequences, edge set and nnz are identical to the original; only the
    weight-to-edge assignment changes. Distinct from degree_preserving_null, which
    rewires endpoints.
    """
    src = np.asarray(src, dtype=np.int64)
    dst = np.asarray(dst, dtype=np.int64)
    w = np.asarray(signed_w, dtype=np.float32).copy()
    rng.shuffle(w)
    out0, in0 = degree_sequences(src, dst, n)
    A = sparse.csr_matrix((w, (dst, src)), shape=(n, n))  # (post, pre)
    coo = A.tocoo()
    out1, in1 = degree_sequences(coo.col, coo.row, n)
    diag = {
        "n_edges_in": int(len(src)),
        "n_edges_out": int(A.nnz),
        "self_loops": int((src == dst).sum()),
        "topology_preserved": bool(np.array_equal(out0, out1) and np.array_equal(in0, in1)),
        "weight_multiset_preserved": bool(np.allclose(np.sort(A.data), np.sort(np.asarray(signed_w, dtype=np.float32)))),
        "fraction_weights_moved": float((w != np.asarray(signed_w, dtype=np.float32)).mean()) if len(w) else 0.0,
    }
    if not diag["topology_preserved"]:
        raise RuntimeError(f"weight permutation changed topology: {diag}")
    return A, diag


def remove_topk_hubs(
    src, dst, signed_w, n: int, k: int
) -> tuple[sparse.csr_matrix, dict]:
    """PROTOCOL ablation: drop edges incident on the k highest out-degree nodes.

    Remaining graph is still indexed 0..n-1 (hubs become isolates). Does not
    renumber, so it can be compared to the full reservoir with the same probes.
    """
    src = np.asarray(src, dtype=np.int64)
    dst = np.asarray(dst, dtype=np.int64)
    w = np.asarray(signed_w, dtype=np.float32)
    k = int(min(max(k, 0), n))
    out_deg = np.bincount(src, minlength=n)
    hubs = np.argsort(out_deg)[-k:] if k else np.array([], dtype=np.int64)
    hub_set = set(hubs.tolist())
    keep = np.array([(int(a) not in hub_set and int(b) not in hub_set) for a, b in zip(src, dst)])
    A = sparse.csr_matrix((w[keep], (dst[keep], src[keep])), shape=(n, n))
    diag = {
        "k": k,
        "hubs": hubs.tolist(),
        "hub_out_degrees": out_deg[hubs].tolist() if k else [],
        "n_edges_in": int(len(src)),
        "n_edges_out": int(A.nnz),
        "edges_removed": int((~keep).sum()),
    }
    return A, diag
