#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import sparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research import motif_mine_001 as DEG
from research import motif_mine_002 as BLOCK

# SOURCE: fixed 500-node subgraph used by the prior structural inventory.
N_SUBGRAPH=500
# SOURCE: MOTIF-MINE-005 protocol.
N_NULLS=20
SEEDS=tuple(range(N_NULLS))
# SOURCE: smoke is one draw per null family and cannot be evidence.
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
    return DEG.choose_nodes(g)

def unsigned_local(g,nodes):
    remap=-np.ones(g.n,dtype=np.int64)
    remap[nodes]=np.arange(len(nodes),dtype=np.int64)
    mask=np.isin(g.src,nodes)&np.isin(g.dst,nodes)
    src=remap[g.src[mask]]
    dst=remap[g.dst[mask]]
    if len(set(zip(src.tolist(),dst.tolist()))) != len(src):
        raise RuntimeError("duplicate source graph edges")
    A=sparse.csr_matrix((np.ones(len(src),dtype=np.int8),(dst,src)),shape=(len(nodes),len(nodes)))
    self_loops=int(A.diagonal().astype(bool).sum())
    A.setdiag(False)
    A.eliminate_zeros()
    return A,self_loops

def graph_diag(A):
    dst,src=A.nonzero()
    return {"n_nodes":int(A.shape[0]),"n_edges":int(A.nnz),"self_loops":int(A.diagonal().astype(bool).sum()),"duplicate_edges":int(len(src)-len(set(zip(src.tolist(),dst.tolist())))),"in_degree":np.diff(A.tocsc().indptr).astype(np.int64).tolist(),"out_degree":np.diff(A.indptr).astype(np.int64).tolist()}

def count_motifs(A):
    B=A.toarray().astype(np.int8)
    noninduced_ffl=0
    induced_ffl=0
    induced_cycle_paths=0
    n=B.shape[0]
    for sink in range(n):
        for middle in np.flatnonzero(B[sink]):
            middle=int(middle)
            if middle==sink:
                continue
            for top in np.flatnonzero(B[middle]):
                top=int(top)
                if top==sink or top==middle:
                    continue
                if B[sink,top]:
                    noninduced_ffl+=1
                if B[top,middle] or B[middle,sink] or B[top,sink]:
                    continue
                if B[sink,top]:
                    induced_ffl+=1
    for source in range(n):
        for middle in np.flatnonzero(B[source]):
            middle=int(middle)
            if middle==source or B[middle,source]:
                continue
            for target in np.flatnonzero(B[middle]):
                target=int(target)
                if target==source or target==middle:
                    continue
                if B[target,source] and not B[source,target] and not B[target,middle]:
                    induced_cycle_paths+=1
    return {"noninduced_feed_forward_loop":int(noninduced_ffl),"induced_feed_forward_loop":int(induced_ffl),"induced_3cycle":int(induced_cycle_paths//3)}

def compare(obs,draws):
    keys=sorted(set(obs).union(*(set(x) for x in draws)))
    out={}
    for key in keys:
        vals=np.asarray([x.get(key,0) for x in draws],dtype=np.float64)
        mean=float(vals.mean())
        sd=float(vals.std(ddof=1)) if len(vals)>1 else None
        out[key]={"observed":int(obs.get(key,0)),"null_mean":mean,"null_sd":sd,"delta":float(obs.get(key,0)-mean),"standardized_delta":float((obs.get(key,0)-mean)/sd) if sd and sd>0 else None}
    return out

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--smoke",action="store_true")
    args=ap.parse_args()
    smoke=bool(args.smoke)
    seeds=SMOKE_SEEDS if smoke else SEEDS
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outroot=ROOT/"research"/"results"/"MOTIF-MINE-005"
    outdir=outroot/(( "SMOKE_" if smoke else "FULL_")+stamp+"_"+git_rev()[:12])
    outdir.mkdir(parents=True)
    protocol=ROOT/"research"/"MOTIF-MINE-005-PROTOCOL.md"
    g=DEG.load_graph(load_neurons=False)
    nodes=choose_nodes(g)
    A,source_self_loops=unsigned_local(g,nodes)
    labels=BLOCK.load_labels()[nodes]
    od=graph_diag(A)
    obs=count_motifs(A)
    meta={"experiment":"MOTIF-MINE-005","mode":"smoke" if smoke else "full","status":"RUNNING","git_tip":git_rev(),"started_utc":utc_now(),"protocol_sha256":sha256_file(protocol),"graph_meta_sha256":sha256_file(ROOT/"data/derived/graph/graph_meta.json"),"selected_nodes":nodes.tolist(),"source_self_loops_removed":source_self_loops,"graph_diag":od,"raw_and_derived_graph_untouched":True}
    write_once(outdir/"metadata.json",meta)
    write_once(outdir/"observed.json",{"motifs":obs,"graph_diag":od,"source_self_loops_removed":source_self_loops})
    print(json.dumps({"outdir":str(outdir),"mode":meta["mode"],"graph_diag":od,"source_self_loops_removed":source_self_loops,"observed":obs,"seeds":[int(x) for x in seeds]}),flush=True)
    degree_draws=[]
    block_draws=[]
    for seed in seeds:
        print("seed",int(seed),flush=True)
        N,dd=DEG.make_null(A,int(seed))
        nd=graph_diag(N)
        if nd["n_edges"]!=od["n_edges"] or nd["self_loops"]!=0 or nd["duplicate_edges"]!=0 or nd["in_degree"]!=od["in_degree"] or nd["out_degree"]!=od["out_degree"]:
            raise RuntimeError("degree null invariant failed")
        dc=count_motifs(N)
        write_once(outdir/("degree-null-%02d.json"%seed),{"seed":int(seed),"counts":dc,"graph_diag":nd,"rewire_diag":dd})
        degree_draws.append(dc)
        N,bd=BLOCK.make_block_null(A,labels,int(seed))
        nd=graph_diag(N)
        if nd["n_edges"]!=od["n_edges"] or nd["self_loops"]!=0 or nd["duplicate_edges"]!=0 or nd["in_degree"]!=od["in_degree"] or nd["out_degree"]!=od["out_degree"] or not bd["block_counts_preserved"]:
            raise RuntimeError("block null invariant failed")
        bc=count_motifs(N)
        write_once(outdir/("block-null-%02d.json"%seed),{"seed":int(seed),"counts":bc,"graph_diag":nd,"rewire_diag":bd})
        block_draws.append(bc)
    summary={"experiment":"MOTIF-MINE-005","mode":meta["mode"],"classification":"SMOKE_NOT_EVIDENCE" if smoke else "STRUCTURAL_MEASURED","observed":obs,"degree_null_draws":degree_draws,"block_null_draws":block_draws,"seeds_completed":[int(x) for x in seeds],"graph_diag":od,"source_self_loops_removed":source_self_loops,"degree_comparison":compare(obs,degree_draws),"block_comparison":compare(obs,block_draws),"claim_scope":"corrected unsigned-edge structural motif inventory only; no biological function, novelty, or ML transfer"}
    write_once(outdir/"summary.json",summary)
    print(json.dumps(summary,indent=2,sort_keys=True),flush=True)
    print("WROTE",outdir/"summary.json",flush=True)

if __name__=="__main__":
    main()
