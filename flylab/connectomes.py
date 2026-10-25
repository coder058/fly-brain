"""Whole-CNS weight matrices for the Shiu et al. model: FlyWire 630 and MaleCNS v1.0.

FlyWire: the exact connectivity table Shiu et al. simulated (`2023_03_23_connectivity_630_
final.parquet` from github.com/philshiu/Drosophila_brain_model, MIT; FlyWire data are
subject to the FlyWire terms). It is not redistributed here: `scripts/fetch_shiu_flywire.sh`
clones that repository. Signs are already in the table.

MaleCNS: built from the full traced graph (`data/derived/graph/`) with Shiu et al.'s sign
rule (GABA and glutamate inhibitory, every other transmitter excitatory), so that the two
connectomes differ only in their wiring and annotations, not in modelling choices.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
SHIU_DIR = ROOT / "external" / "Drosophila_brain_model"


@dataclass
class Connectome:
    name: str
    W: sparse.csr_matrix          # (post, pre) signed synapse counts
    ids: np.ndarray               # FlyWire root IDs or MaleCNS body IDs, index-aligned
    meta: dict

    @property
    def n(self) -> int:
        return self.W.shape[0]

    def index_of(self, ids) -> np.ndarray:
        pos = {int(x): i for i, x in enumerate(self.ids)}
        missing = [int(x) for x in ids if int(x) not in pos]
        if missing:
            raise KeyError(f"{len(missing)} ids not in {self.name}: {missing[:5]}")
        return np.array([pos[int(x)] for x in ids], dtype=np.int64)


def load_flywire_630(shiu_dir: Path = SHIU_DIR) -> Connectome:
    import pandas as pd
    import pyarrow.parquet as pq

    comp = pd.read_csv(shiu_dir / "2023_03_23_completeness_630_final.csv", index_col=0)
    con = pq.read_table(shiu_dir / "2023_03_23_connectivity_630_final.parquet",
                        columns=["Presynaptic_Index", "Postsynaptic_Index",
                                 "Excitatory x Connectivity"]).to_pandas()
    n = len(comp)
    W = sparse.csr_matrix((con["Excitatory x Connectivity"].to_numpy(np.float64),
                           (con["Postsynaptic_Index"].to_numpy(), con["Presynaptic_Index"].to_numpy())),
                          shape=(n, n))
    return Connectome("FlyWire 630", W, comp.index.to_numpy(np.int64),
                      {"n_neurons": n, "n_edges": int(len(con)),
                       "synapses": int(np.abs(con["Excitatory x Connectivity"]).sum())})


def load_malecns_shiu_signs() -> Connectome:
    import pyarrow.feather as feather

    from flylab.brain import shiu_sign
    from flylab.graph import GRAPH_DIR, load_graph

    g = load_graph()
    nt = feather.read_table(ROOT / "data/raw/malecns_v1/body-neurotransmitters-male-cns-v1.0.feather",
                            columns=["body", "ground_truth", "consensus_nt"]).to_pandas()
    gt = nt["ground_truth"].where(nt["ground_truth"].notna() & (nt["ground_truth"].astype(str) != ""),
                                  nt["consensus_nt"])
    sign_by_body = dict(zip(nt["body"].to_numpy(np.int64), (shiu_sign(x) for x in gt), strict=True))
    signs = np.array([sign_by_body.get(int(b), 1) for b in g.body_ids], dtype=np.float64)
    W = sparse.csr_matrix((g.weight.astype(np.float64) * signs[g.src], (g.dst, g.src)),
                          shape=(g.n, g.n))
    meta = {"n_neurons": g.n, "n_edges": int(W.nnz), "synapses": int(g.weight.sum()),
            "inhibitory_neurons": int((signs < 0).sum()), "graph_dir": str(GRAPH_DIR)}
    return Connectome("MaleCNS v1.0", W, np.asarray(g.body_ids, dtype=np.int64), meta)
