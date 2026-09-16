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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research import motif_mine_001 as DEG
from research import motif_mine_002 as BLOCK

N_NULLS=20
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
    return DEG.choose_nodes(g)

def signed_edges(g,nodes):
    n=len(nodes)
    remap=-np.ones(g.n,dtype=np.int64)
    remap[nodes]=np.arange(n,dtype=np.int64)
    mask=np.isin(g.src,nodes)&np.isin(g.dst,nodes)
    src=remap[g.src[mask]]
    dst=remap[g.dst[mask]]
    weights=np.asarray(g.signed_weight[mask],dtype=np.float32)
    if len(set(zip(src.tolist(),dst.tolist()))) != len(src):
        raise RuntimeError("duplicate source graph edges")
    return src,dst,weights

def matrices(src,dst,weights,n):
    present=np.zeros((n,n),dtype=np.bool_)
    codes=np.full((n,n),9,dtype=np.int8)
    present[dst,src]=True
    codes[dst,src]=np.where(weights>0,1,np.where(weights<0,-1,0)).astype(np.int8)
    return present,codes

def count_signs(src,dst,weights,n):
    present,codes=matrices(src,dst,weights,n)
    counts=defaultdict(int)
    for sink in range(n):
        for middle in np.flatnonzero(present[sink]):
            middle=int(middle)
            if middle==sink or present[middle,sink]:
                continue
            for top in np.flatnonzero(present[middle]):
                top=int(top)
                if top==sink or top==middle:
                    continue
                if present[top,middle]:
                    continue
                if present[sink,top] and not present[top,sink]:
                    chars=[]
                    for a,b in ((top,middle),(middle,sink),(top,sink)):
                        code=int(codes[b,a])
                        chars.append("p" if code>0 else "n" if code<0 else "u")
                    counts["".join(chars)]+=1
    return dict(sorted(counts.items()))

def summaries(counts):
    return {"all_positive":int(counts.get("ppp",0)),"any_inhibitory":int(sum(v for k,v in counts.items() if "n" in k)),"total_induced_ffl":int(sum(counts.values()))}

def null_edges_from_matrix(N):
    dst,src=N.nonzero()
    return src.astype(np.int64),dst.astype(np.int64),np.asarray(N.data,dtype=np.float32)

def degree_null(src,dst,weights,seed,n):
    encoded=np.asarray(weights,dtype=np.float32).copy()
    encoded[encoded==0]=np.nan
    rng=np.random.default_rng([99331,int(seed)])
    N,diag=DEG.degree_preserving_null(src,dst,encoded,n,rng,n_swaps_per_edge=20)
    ns,nd,nw=null_edges_from_matrix(N)
    nw=np.where(np.isnan(nw),0.0,nw)
    return ns,nd,nw,diag

def block_null(src,dst,weights,labels,seed,n):
    encoded=np.asarray(weights,dtype=np.float32).copy()
    encoded[encoded==0]=np.nan
    rng=np.random.default_rng([99332,int(seed)])
    # Reuse the audited block swap logic with an explicit nonzero unknown sentinel.
    original_dst=dst.copy()
    present=set(zip(src.tolist(),dst.tolist()))
    blocks=defaultdict(list)
    for i,(a,b) in enumerate(zip(src,dst)):
        blocks[(str(labels[a]),str(labels[b]))].append(i)
    accepted_total=0
    reports={}
    for block,raw in sorted(blocks.items()):
        indices=np.asarray(raw,dtype=np.int64)
        target=int(len(indices)*20)
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
            present.discard((a,b)); present.discard((c,d))
            present.add((a,d)); present.add((c,b))
            dst[i],dst[j]=d,b
            accepted+=1
        accepted_total+=accepted
        reports["|".join(block)]={"edges":int(len(indices)),"accepted_swaps":int(accepted),"target_swaps":int(target),"attempts":int(attempts)}
    N=sparse.csr_matrix((encoded,(dst,src)),shape=(n,n))
    ns,nd,nw=null_edges_from_matrix(N)
    nw=np.where(np.isnan(nw),0.0,nw)
    original_blocks=[(str(labels[a]),str(labels[b])) for a,b in zip(src,original_dst)]
    new_blocks=[(str(labels[a]),str(labels[b])) for a,b in zip(src,dst)]
    diag={"n_edges_in":int(len(src)),"n_edges_out":int(N.nnz),"duplicate_edges":int(len(src)-len(set(zip(ns.tolist(),nd.tolist())))),"self_loops":int(np.sum(ns==nd)),"block_counts_preserved":bool(sorted(original_blocks)==sorted(new_blocks)),"accepted_swaps":int(accepted_total),"blocks":reports}
    return ns,nd,nw,diag

def compare(obs,draws):
    keys=sorted(set(obs).union(*(set(x) for x in draws)))
    out={}
    for key in keys:
        vals=np.asarray([x.get(key,0) for x in draws],dtype=np.float64)
        mean=float(vals.mean())
        sd=float(vals.std(ddof=1)) if len(vals)>1 else None
        out[key]={"observed":int(obs.get(key,0)),"null_mean":mean,"null_sd":sd,"delta":float(obs.get(key,0)-mean)}
    return out

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--smoke",action="store_true")
    args=ap.parse_args()
    smoke=bool(args.smoke)
    seeds=SMOKE_SEEDS if smoke else SEEDS
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outroot=ROOT/"research"/"results"/"SPECIALIZATION-001"
    outdir=outroot/(( "SMOKE_" if smoke else "FULL_")+stamp+"_"+git_rev()[:12])
    outdir.mkdir(parents=True)
    protocol=ROOT/"research"/"SPECIALIZATION-001-PROTOCOL.md"
    g=DEG.load_graph(load_neurons=False)
    nodes=choose_nodes(g)
    src,dst,weights=signed_edges(g,nodes)
    labels=BLOCK.load_labels()[nodes]
    n=len(nodes)
    present,codes=matrices(src,dst,weights,n)
    if int(present.sum()) != len(src):
        raise RuntimeError("edge matrix mismatch")
    obs=count_signs(src,dst,weights,n)
    diag={"n_nodes":n,"n_edges":int(len(src)),"self_loops":int(np.sum(src==dst)),"duplicate_edges":int(len(src)-len(set(zip(src.tolist(),dst.tolist())))),"in_degree":present.sum(axis=1).astype(int).tolist(),"out_degree":present.sum(axis=0).astype(int).tolist()}
    meta={"experiment":"SPECIALIZATION-001","mode":"smoke" if smoke else "full","status":"RUNNING","git_tip":git_rev(),"started_utc":utc_now(),"protocol_sha256":sha256_file(protocol),"graph_meta_sha256":sha256_file(ROOT/"data/derived/graph/graph_meta.json"),"selected_nodes":nodes.tolist(),"graph_diag":diag,"raw_and_derived_graph_untouched":True}
    write_once(outdir/"metadata.json",meta)
    write_once(outdir/"observed.json",{"pattern_counts":obs,"summary":summaries(obs),"graph_diag":diag})
    print(json.dumps({"outdir":str(outdir),"mode":meta["mode"],"observed_summary":summaries(obs),"seeds":[int(x) for x in seeds]}),flush=True)
    degree_draws=[]
    block_draws=[]
    for seed in seeds:
        print("seed",int(seed),flush=True)
        ns,nd,nw,dd=degree_null(src,dst,weights,int(seed),n)
        p,c=matrices(ns,nd,nw,n)
        gd={"n_nodes":n,"n_edges":int(p.sum()),"in_degree":p.sum(axis=1).astype(int).tolist(),"out_degree":p.sum(axis=0).astype(int).tolist(),"self_loops":int(np.sum(ns==nd)),"duplicate_edges":int(len(ns)-len(set(zip(ns.tolist(),nd.tolist()))))}
        if gd["n_edges"]!=diag["n_edges"] or gd["in_degree"]!=diag["in_degree"] or gd["out_degree"]!=diag["out_degree"] or gd["self_loops"]!=0 or gd["duplicate_edges"]!=0:
            raise RuntimeError("degree null invariant failed")
        dc=count_signs(ns,nd,nw,n)
        write_once(outdir/("degree-null-%02d.json"%seed),{"seed":int(seed),"pattern_counts":dc,"summary":summaries(dc),"graph_diag":gd,"rewire_diag":dd})
        degree_draws.append(dc)
        ns,nd,nw,bd=block_null(src.copy(),dst.copy(),weights,labels,int(seed),n)
        p,c=matrices(ns,nd,nw,n)
        gd={"n_nodes":n,"n_edges":int(p.sum()),"in_degree":p.sum(axis=1).astype(int).tolist(),"out_degree":p.sum(axis=0).astype(int).tolist(),"self_loops":int(np.sum(ns==nd)),"duplicate_edges":int(len(ns)-len(set(zip(ns.tolist(),nd.tolist()))))}
        if gd["n_edges"]!=diag["n_edges"] or gd["in_degree"]!=diag["in_degree"] or gd["out_degree"]!=diag["out_degree"] or gd["self_loops"]!=0 or gd["duplicate_edges"]!=0 or not bd["block_counts_preserved"]:
            raise RuntimeError("block null invariant failed")
        bc=count_signs(ns,nd,nw,n)
        write_once(outdir/("block-null-%02d.json"%seed),{"seed":int(seed),"pattern_counts":bc,"summary":summaries(bc),"graph_diag":gd,"rewire_diag":bd})
        block_draws.append(bc)
    summary={"experiment":"SPECIALIZATION-001","mode":meta["mode"],"classification":"SMOKE_NOT_EVIDENCE" if smoke else "STRUCTURAL_MEASURED","observed_pattern_counts":obs,"observed_summary":summaries(obs),"degree_null_summaries":[summaries(x) for x in degree_draws],"block_null_summaries":[summaries(x) for x in block_draws],"degree_comparison":compare(obs,degree_draws),"block_comparison":compare(obs,block_draws),"seeds_completed":[int(x) for x in seeds],"claim_scope":"signed structural motif composition only; no biological function, novelty, or ML transfer"}
    write_once(outdir/"summary.json",summary)
    print(json.dumps(summary,indent=2,sort_keys=True),flush=True)
    print("WROTE",outdir/"summary.json",flush=True)

if __name__=="__main__":
    main()
