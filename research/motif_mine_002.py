#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import sparse
import pyarrow.feather as feather

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flylab.graph import load_graph, induced_subgraph
from flylab.nulls import degree_preserving_null

N_SUBGRAPH=500
N_NULLS=20
SWAPS_PER_EDGE=20
SEEDS=tuple(range(N_NULLS))
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

def load_labels():
    table=feather.read_table(ROOT/"data/derived/graph/neurons.feather",columns=["neuron_id","superclass"]).to_pydict()
    ids=np.asarray(table["neuron_id"],dtype=np.int64)
    if not np.array_equal(ids,np.arange(len(ids),dtype=np.int64)):
        raise RuntimeError("neuron annotation order mismatch")
    return np.asarray([str(x) if x not in (None,"") else "UNANNOTATED" for x in table["superclass"]],dtype=str)

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
    return {"n_nodes":int(A.shape[0]),"n_edges":int(A.nnz),"self_loops":int(A.diagonal().astype(bool).sum()),"duplicate_edges":int(len(src)-len(set(zip(src.tolist(),dst.tolist())))),"in_degree":np.diff(A.tocsc().indptr).astype(np.int64).tolist(),"out_degree":np.diff(A.indptr).astype(np.int64).tolist()}

def cycle3(A):
    return int(A.dot(A).dot(A).diagonal().sum()//3)

def feed_forward(A):
    dense=A.toarray().astype(np.int8)
    total=0
    for source in range(dense.shape[0]):
        for middle in np.flatnonzero(dense[source]):
            if int(middle)==source:
                continue
            targets=np.flatnonzero(dense[middle])
            total+=int(np.sum(dense[source,targets]))
    return int(total)

def count_motifs(A):
    return {"directed_3cycle":cycle3(A),"feed_forward_loop":feed_forward(A)}

def make_block_null(A,labels,seed):
    src,dst,weights=edge_arrays(A)[0],edge_arrays(A)[1],np.ones(A.nnz,dtype=np.float32)
    original_dst=dst.copy()
    rng=np.random.default_rng([99221,int(seed)])
    present=set(zip(src.tolist(),dst.tolist()))
    blocks=defaultdict(list)
    for i,(a,b) in enumerate(zip(src,dst)):
        blocks[(str(labels[a]),str(labels[b]))].append(i)
    accepted_total=0
    attempts_total=0
    reports={}
    for block,raw in sorted(blocks.items()):
        indices=np.asarray(raw,dtype=np.int64)
        target=int(len(indices)*SWAPS_PER_EDGE)
        accepted=0
        attempts=0
        max_attempts=max(20,target*10)
        while accepted<target and attempts<max_attempts and len(indices)>1:
            attempts+=1
            i,j=rng.choice(indices,size=2,replace=False)
            a,b=int(src[i]),int(dst[i])
            c,d=int(src[j]),int(dst[j])
            if a==d or c==b or (a,d) in present or (c,b) in present:
                continue
            present.discard((a,b))
            present.discard((c,d))
            present.add((a,d))
            present.add((c,b))
            dst[i],dst[j]=d,b
            accepted+=1
        accepted_total+=accepted
        attempts_total+=attempts
        reports["|".join(block)]={"edges":int(len(indices)),"accepted_swaps":int(accepted),"target_swaps":int(target),"attempts":int(attempts)}
    N=sparse.csr_matrix((weights,(dst,src)),shape=A.shape)
    original_blocks=[(str(labels[a]),str(labels[b])) for a,b in zip(src,original_dst)]
    new_blocks=[(str(labels[a]),str(labels[b])) for a,b in zip(src,dst)]
    diag={"n_edges_in":int(len(src)),"n_edges_out":int(N.nnz),"duplicate_edges":int(len(src)-len(set(zip(src.tolist(),dst.tolist())))),"self_loops":int(np.sum(src==dst)),"block_counts_preserved":bool(sorted(original_blocks)==sorted(new_blocks)),"accepted_swaps":int(accepted_total),"attempts":int(attempts_total),"blocks":reports}
    return N.astype(bool).tocsr(),diag

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--smoke",action="store_true")
    args=ap.parse_args()
    smoke=bool(args.smoke)
    seeds=SMOKE_SEEDS if smoke else SEEDS
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outroot=ROOT/"research"/"results"/"MOTIF-MINE-002"
    outdir=outroot/(( "SMOKE_" if smoke else "FULL_")+stamp+"_"+git_rev()[:12])
    outdir.mkdir(parents=True)
    protocol=ROOT/"research"/"MOTIF-MINE-002-PROTOCOL.md"
    g=load_graph(load_neurons=False)
    nodes=choose_nodes(g)
    labels=load_labels()[nodes]
    A=local_graph(g,nodes)
    od=graph_diag(A)
    meta={"experiment":"MOTIF-MINE-002","mode":"smoke" if smoke else "full","status":"RUNNING","git_tip":git_rev(),"started_utc":utc_now(),"protocol_sha256":sha256_file(protocol),"graph_meta_sha256":sha256_file(ROOT/"data/derived/graph/graph_meta.json"),"selected_nodes":nodes.tolist(),"selected_labels":sorted(set(labels.tolist())),"graph_diag":od,"raw_and_derived_graph_untouched":True}
    write_once(outdir/"metadata.json",meta)
    observed=count_motifs(A)
    write_once(outdir/"observed.json",{"motifs":observed,"graph_diag":od})
    print(json.dumps({"outdir":str(outdir),"mode":meta["mode"],"graph_diag":od,"observed":observed,"seeds":[int(x) for x in seeds]}),flush=True)
    nulls=[]
    for seed in seeds:
        print("null",int(seed),flush=True)
        N,diag=make_block_null(A,labels,int(seed))
        nd=graph_diag(N)
        if nd["n_nodes"]!=od["n_nodes"] or nd["n_edges"]!=od["n_edges"] or nd["self_loops"]!=0 or nd["duplicate_edges"]!=0 or nd["in_degree"]!=od["in_degree"] or nd["out_degree"]!=od["out_degree"] or not diag["block_counts_preserved"]:
            raise RuntimeError("block null invariant failed")
        counts=count_motifs(N)
        row={"seed":int(seed),"counts":counts,"graph_diag":nd,"rewire_diag":diag}
        write_once(outdir/("null-%02d.json"%seed),row)
        nulls.append(counts)
    summary={"experiment":"MOTIF-MINE-002","mode":meta["mode"],"classification":"SMOKE_NOT_EVIDENCE" if smoke else "STRUCTURAL_MEASURED","observed":observed,"null_draws":nulls,"seeds_completed":[int(x) for x in seeds],"graph_diag":od,"claim_scope":"structural block-control only; no biological function, novelty, or ML transfer"}
    if not smoke:
        for name in observed:
            vals=np.asarray([x[name] for x in nulls],dtype=np.float64)
            mean=float(vals.mean())
            sd=float(vals.std(ddof=1)) if len(vals)>1 else None
            summary.setdefault("comparison",{})[name]={"observed":int(observed[name]),"null_mean":mean,"null_sd":sd,"delta":float(observed[name]-mean),"standardized_delta":float((observed[name]-mean)/sd) if sd and sd>0 else None}
    write_once(outdir/"summary.json",summary)
    print(json.dumps(summary,indent=2,sort_keys=True),flush=True)
    print("WROTE",outdir/"summary.json",flush=True)

if __name__=="__main__":
    main()
