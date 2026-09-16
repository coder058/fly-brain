#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import sparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flylab.graph import load_graph, induced_subgraph
from flylab.nulls import degree_preserving_null

# SOURCE: exact fixed subgraph used by CIRCUIT-MINE and ROUTING.
N_SUBGRAPH=500
# SOURCE: MOTIF-MINE-001 protocol.
N_NULLS=20
# SOURCE: existing degree-preserving null setting.
SWAPS_PER_EDGE=20
SEEDS=tuple(range(N_NULLS))
# SOURCE: smoke is one null and cannot be evidence.
SMOKE_SEEDS=(0,)

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()

def git_rev()->str:
    p=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD"],capture_output=True,text=True,timeout=10)
    return p.stdout.strip() or "unknown"

def utc_now()->str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def write_once(path:Path,obj:dict)->None:
    if path.exists():
        raise RuntimeError("refusing to overwrite "+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,default=str)+chr(10),encoding="utf-8")
    tmp.replace(path)

def choose_nodes(g):
    degree=np.diff(g.csr.indptr).astype(np.int64,copy=False)
    return np.sort(np.argsort(degree)[-N_SUBGRAPH:])

def local_graph(g,nodes):
    A,_=induced_subgraph(g,nodes)
    A=A.astype(bool).tocsr()
    A.setdiag(False)
    A.eliminate_zeros()
    return A

def edge_arrays(A):
    dst,src=A.nonzero()
    return src.astype(np.int64),dst.astype(np.int64)

def graph_diag(A):
    src,dst=edge_arrays(A)
    return {
        "n_nodes":int(A.shape[0]),
        "n_edges":int(A.nnz),
        "self_loops":int(A.diagonal().astype(bool).sum()),
        "duplicate_edges":int(len(src)-len(set(zip(src.tolist(),dst.tolist())))),
        "in_degree":np.diff(A.tocsc().indptr).astype(np.int64).tolist(),
        "out_degree":np.diff(A.indptr).astype(np.int64).tolist(),
    }

def cycle3(A):
    B=A.dot(A)
    C=B.dot(A)
    return int(C.diagonal().sum()//3)

def feed_forward(A):
    dense=A.toarray().astype(np.int8)
    total=0
    n=dense.shape[0]
    for source in range(n):
        out=np.flatnonzero(dense[source])
        for middle in out:
            if middle==source:
                continue
            targets=np.flatnonzero(dense[middle])
            total+=int(np.sum(dense[source,targets]))
    return int(total)

def count_motifs(A):
    return {"directed_3cycle":cycle3(A),"feed_forward_loop":feed_forward(A)}

def make_null(A,seed):
    src,dst=edge_arrays(A)
    rng=np.random.default_rng([99117,int(seed)])
    W,diag=degree_preserving_null(src,dst,np.ones(len(src),dtype=np.float32),A.shape[0],rng,n_swaps_per_edge=SWAPS_PER_EDGE)
    N=(W!=0).astype(bool).tocsr()
    N.setdiag(False)
    N.eliminate_zeros()
    nd=graph_diag(N)
    od=graph_diag(A)
    if nd["n_edges"] != od["n_edges"]:
        raise RuntimeError("null edge count changed")
    if nd["in_degree"] != od["in_degree"]:
        raise RuntimeError("null in-degree sequence changed")
    if nd["out_degree"] != od["out_degree"]:
        raise RuntimeError("null out-degree sequence changed")
    return N,diag

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--smoke",action="store_true")
    args=ap.parse_args()
    smoke=bool(args.smoke)
    seeds=SMOKE_SEEDS if smoke else SEEDS
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outroot=ROOT/"research"/"results"/"MOTIF-MINE-001"
    outdir=outroot/(( "SMOKE_" if smoke else "FULL_")+stamp+"_"+git_rev()[:12])
    outdir.mkdir(parents=True)
    protocol=ROOT/"research"/"MOTIF-MINE-001-PROTOCOL.md"
    g=load_graph(load_neurons=False)
    nodes=choose_nodes(g)
    A=local_graph(g,nodes)
    observed_diag=graph_diag(A)
    meta={"experiment":"MOTIF-MINE-001","mode":"smoke" if smoke else "full","status":"RUNNING","git_tip":git_rev(),"started_utc":utc_now(),"protocol_sha256":sha256_file(protocol),"graph_meta_sha256":sha256_file(ROOT/"data/derived/graph/graph_meta.json"),"selected_nodes":nodes.tolist(),"graph_diag":observed_diag,"raw_and_derived_graph_untouched":True}
    write_once(outdir/"metadata.json",meta)
    print(json.dumps({"outdir":str(outdir),"mode":meta["mode"],"graph_diag":observed_diag,"seeds":[int(x) for x in seeds]}),flush=True)
    obs=count_motifs(A)
    write_once(outdir/"observed.json",{"motifs":obs,"graph_diag":observed_diag})
    nulls=[]
    for seed in seeds:
        print("null",int(seed),flush=True)
        N,rewire_diag=make_null(A,int(seed))
        counts=count_motifs(N)
        row={"seed":int(seed),"counts":counts,"rewire_diag":rewire_diag}
        write_once(outdir/("null-%02d.json"%seed),row)
        nulls.append(counts)
    summary={"experiment":"MOTIF-MINE-001","mode":meta["mode"],"classification":"SMOKE_NOT_EVIDENCE" if smoke else "STRUCTURAL_MEASURED","observed":obs,"null_draws":nulls,"seeds_completed":[int(x) for x in seeds],"graph_diag":observed_diag,"claim_scope":"structural motif inventory only; no biological function, novelty, or ML transfer"}
    if not smoke:
        for name in obs:
            vals=np.asarray([x[name] for x in nulls],dtype=np.float64)
            mean=float(vals.mean())
            sd=float(vals.std(ddof=1)) if len(vals)>1 else None
            summary.setdefault("comparison",{})[name]={"observed":int(obs[name]),"null_mean":mean,"null_sd":sd,"delta":float(obs[name]-mean),"standardized_delta":float((obs[name]-mean)/sd) if sd and sd>0 else None}
    write_once(outdir/"summary.json",summary)
    print(json.dumps(summary,indent=2,sort_keys=True),flush=True)
    print("WROTE",outdir/"summary.json",flush=True)

if __name__=="__main__":
    main()
