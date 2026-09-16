"""Leakage-resistant binary cue/recall task helpers for EXP-MEM-001."""
from __future__ import annotations

import numpy as np

from flylab.dynamics import LIFParams, LIFState, step_lif


def make_binary_trials(n_nodes, input_ids, trials_per_class, lag, cue_amplitude, seed):
    """Deliver a balanced cue once at onset; every later external-current value is zero."""
    labels = np.tile(np.arange(2, dtype=np.int64), int(trials_per_class))
    np.random.default_rng(seed).shuffle(labels)
    # SOURCE: the task contract is a single time-zero cue followed by a silent delay.
    currents = np.zeros((len(labels), int(lag) + 1, int(n_nodes)), dtype=np.float32)
    currents[:, 0, np.asarray(input_ids, dtype=np.int64)] = (
        labels[:, None].astype(np.float32) * float(cue_amplitude)
    )
    return currents, labels


def simulate_terminal_features(W, currents, lif: LIFParams, input_ids, probe_ids, seed):
    """Return only non-input probe spikes at the final step, never earlier bins."""
    n = W.shape[0]
    input_ids = np.asarray(input_ids, dtype=np.int64)
    probe_ids = np.asarray(probe_ids, dtype=np.int64)
    if np.intersect1d(input_ids, probe_ids).size:
        raise ValueError("input/probe overlap would expose the cue to the readout")
    pool = np.ones(n, dtype=bool)
    pool[input_ids] = False
    X = np.zeros((len(currents), len(probe_ids)), dtype=np.float32)
    pool_spikes = 0.0
    probe_spikes = 0.0
    for trial, drive in enumerate(currents):
        # SOURCE: match the initialization distribution in flylab.dynamics.simulate.
        rng = np.random.default_rng([int(seed), int(trial)])
        state = LIFState(
            v=rng.normal(lif.v_rest, 0.05, size=n).astype(np.float32),
            spikes=np.zeros(n, dtype=np.float32),
        )
        for step, current in enumerate(drive):
            state = step_lif(W, state, current, lif)
            pool_spikes += float(state.spikes[pool].sum())
            if step == len(drive) - 1:
                # SOURCE: the registered observation is the state at probe time only.
                X[trial] = state.spikes[probe_ids]
                probe_spikes += float(state.spikes[probe_ids].sum())
    return X, {
        "pool_spikes": pool_spikes,
        "probe_spikes": probe_spikes,
        "n_trials": int(len(currents)),
        "n_steps": int(currents.shape[1]),
        "pool_size": int(pool.sum()),
    }


def delay_line_recall(cue, lag, capacity):
    """Known-memory FIFO positive control; zero is the no-cue fill value."""
    if lag > capacity:
        return 0
    state = [0] * (capacity + 1)
    state[0] = int(cue)
    for _ in range(int(lag)):
        state[1:] = state[:-1]
        state[0] = 0
    return int(state[int(lag)])


def combine_split_liveness(summary, train, test):
    """Require usable features in both independent splits, not just their union."""
    failed = [name for name, report in (("train", train), ("test", test))
              if not report["alive"]]
    result = {**summary, "split_liveness": {"train": train, "test": test},
              "failed_splits": failed,
              "alive": bool(summary["alive"] and not failed)}
    if failed:
        result["dead_reason"] = "feature/liveness guard failed in split(s): " + ", ".join(failed)
    return result
