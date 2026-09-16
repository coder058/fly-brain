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

def induced_feed_forward(A):
    dense=A.toarray().astype(np.int8)
    total=0
    for source in range(dense.shape[0]):
        for middle in np.flatnonzero(dense[source]):
            if int(middle)==source or dense[middle,source]:
                continue
            for target in np.flatnonzero(dense[middle]):
                target=int(target)
                if target==source or target==int(middle):
                    continue
                if dense[target,int(middle)]:
                    continue
                if dense[source,target] and not dense[target,source]:
                    total+=1
    return int(total)

def induced_cycle(A):
    dense=A.toarray().astype(np.int8)
    total=0
    for source in range(dense.shape[0]):
        for middle in np.flatnonzero(dense[source]):
            middle=int(middle)
            if middle==source or dense[middle,source]:
                continue
            for target in np.flatnonzero(dense[middle]):
                target=int(target)
                if target==source or target==middle:
                    continue
                if dense[target,source] and not dense[source,target] and not dense[target,middle]:
                    total+=1
    return int(total//3)

def count(A):
    return {"induced_3cycle":induced_cycle(A),"induced_feed_forward_loop":induced_feed_forward(A)}

def compare(obs,draws):
    out={}
    for name in obs:
        vals=np.asarray([x[name] for x in draws],dtype=np.float64)
        mean=float(vals.mean())
        sd=float(vals.std(ddof=1)) if len(vals)>1 else None
        out[name]={"observed":int(obs[name]),"null_mean":mean,"null_sd":sd,"delta":float(obs[name]-mean),"standardized_delta":float((obs[name]-mean)/sd) if sd and sd>0 else None}
    return out

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--smoke",action="store_true")
    args=ap.parse_args()
    smoke=bool(args.smoke)
    seeds=SMOKE_SEEDS if smoke else SEEDS
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outroot=ROOT/"research"/"results"/"MOTIF-MINE-003"
    outdir=outroot/(( "SMOKE_" if smoke else "FULL_")+stamp+"_"+git_rev()[:12])
    outdir.mkdir(parents=True)
    protocol=ROOT/"research"/"MOTIF-MINE-003-PROTOCOL.md"
    g=DEG.load_graph(load_neurons=False)
    nodes=DEG.choose_nodes(g)
    labels=BLOCK.load_labels()[nodes]
    A=DEG.local_graph(g,nodes)
    od=DEG.graph_diag(A)
    obs=count(A)
    meta={"experiment":"MOTIF-MINE-003","mode":"smoke" if smoke else "full","status":"RUNNING","git_tip":git_rev(),"started_utc":utc_now(),"protocol_sha256":sha256_file(protocol),"graph_meta_sha256":sha256_file(ROOT/"data/derived/graph/graph_meta.json"),"selected_nodes":nodes.tolist(),"graph_diag":od,"raw_and_derived_graph_untouched":True}
    write_once(outdir/"metadata.json",meta)
    write_once(outdir/"observed.json",{"motifs":obs,"graph_diag":od})
    print(json.dumps({"outdir":str(outdir),"mode":meta["mode"],"graph_diag":od,"observed":obs,"seeds":[int(x) for x in seeds]}),flush=True)
    degree_draws=[]
    block_draws=[]
    for seed in seeds:
        print("seed",int(seed),flush=True)
        N,dd=DEG.make_null(A,int(seed))
        nd=DEG.graph_diag(N)
        if nd["n_edges"]!=od["n_edges"] or nd["self_loops"]!=0 or nd["duplicate_edges"]!=0 or nd["in_degree"]!=od["in_degree"] or nd["out_degree"]!=od["out_degree"]:
            raise RuntimeError("degree null invariant failed")
        dc=count(N)
        write_once(outdir/("degree-null-%02d.json"%seed),{"seed":int(seed),"counts":dc,"graph_diag":nd,"rewire_diag":dd})
        degree_draws.append(dc)
        N,bd=BLOCK.make_block_null(A,labels,int(seed))
        nd=DEG.graph_diag(N)
        if nd["n_edges"]!=od["n_edges"] or nd["self_loops"]!=0 or nd["duplicate_edges"]!=0 or nd["in_degree"]!=od["in_degree"] or nd["out_degree"]!=od["out_degree"] or not bd["block_counts_preserved"]:
            raise RuntimeError("block null invariant failed")
        bc=count(N)
        write_once(outdir/("block-null-%02d.json"%seed),{"seed":int(seed),"counts":bc,"graph_diag":nd,"rewire_diag":bd})
        block_draws.append(bc)
    summary={"experiment":"MOTIF-MINE-003","mode":meta["mode"],"classification":"SMOKE_NOT_EVIDENCE" if smoke else "STRUCTURAL_MEASURED","observed":obs,"degree_null_draws":degree_draws,"block_null_draws":block_draws,"seeds_completed":[int(x) for x in seeds],"graph_diag":od,"claim_scope":"induced structural motif control only; no biological function, novelty, or ML transfer"}
    if not smoke:
        summary["degree_comparison"]=compare(obs,degree_draws)
        summary["block_comparison"]=compare(obs,block_draws)
    write_once(outdir/"summary.json",summary)
    print(json.dumps(summary,indent=2,sort_keys=True),flush=True)
    print("WROTE",outdir/"summary.json",flush=True)

if __name__=="__main__":
    main()
