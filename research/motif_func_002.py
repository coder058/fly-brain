#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import sparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research import routing_003 as R
from research import motif_mine_005 as M5

# SOURCE: MOTIF-FUNC-002 protocol.
MIN_PAIRED_SEEDS=8
# SOURCE: MOTIF-FUNC-002 protocol, independent weight permutation stream.
WEIGHT_STREAM=70808
# SOURCE: MOTIF-FUNC-002 protocol; matches M7B accepted swaps per unit.
SWAPS_PER_UNIT=20

def weighted_edges(g,nodes):
    remap=-np.ones(g.n,dtype=np.int64)
    remap[nodes]=np.arange(len(nodes),dtype=np.int64)
    mask=np.isin(g.src,nodes)&np.isin(g.dst,nodes)
    src=remap[g.src[mask]]
    dst=remap[g.dst[mask]]
    w=np.asarray(g.signed_weight[mask],dtype=np.float32)
    keep=src!=dst
    src=src[keep]; dst=dst[keep]; w=w[keep]
    if len(set(zip(src.tolist(),dst.tolist())))!=len(src):
        raise RuntimeError("duplicate weighted source edges")
    return src,dst,w

def edge_set(src,dst):
    return {(int(a),int(b)) for a,b in zip(src,dst)}

def reciprocal_count(edges):
    return int(sum(1 for a,b in edges if (b,a) in edges)//2)

def block_counts(edges,labels):
    out={}
    for a,b in edges:
        k=(str(labels[a]),str(labels[b]))
        out[k]=out.get(k,0)+1
    return dict(sorted(out.items()))

def split_units(src,dst,w):
    weights={(int(a),int(b)):float(x) for a,b,x in zip(src,dst,w)}
    edges=set(weights); seen=set(); singles=[]; pairs=[]
    for a,b in sorted(edges):
        if (a,b) in seen:
            continue
        if a!=b and (b,a) in edges:
            pairs.append([a,b,weights[(a,b)],weights[(b,a)]])
            seen.add((a,b)); seen.add((b,a))
        else:
            singles.append([a,b,weights[(a,b)]])
            seen.add((a,b))
    return singles,pairs,weights

def swap_single_units(present,weights,singles,rng):
    target=len(singles)*SWAPS_PER_UNIT
    cap=max(20,target*10)
    accepted=0; attempts=0
    while accepted<target and attempts<cap:
        attempts+=1
        i,j=rng.choice(len(singles),size=2,replace=False)
        a,b,w1=singles[int(i)]; c,d,w2=singles[int(j)]
        old={(a,b),(c,d)}
        present.difference_update(old)
        weights.pop((a,b)); weights.pop((c,d))
        new={(a,d),(c,b)}
        valid=(a!=d and c!=b and len(new)==2 and new!=old and not (new&present) and not any((y,x) in present or (y,x) in new for x,y in new))
        if valid:
            present.update(new)
            weights[(a,d)]=w1; weights[(c,b)]=w2
            singles[int(i)]=[a,d,w1]; singles[int(j)]=[c,b,w2]
            accepted+=1
        else:
            present.update(old)
            weights[(a,b)]=w1; weights[(c,d)]=w2
    return {"units":len(singles),"target_swaps":target,"accepted_swaps":accepted,"attempts":attempts,"complete":accepted==target}

def swap_pair_units(present,weights,pairs,rng):
    target=len(pairs)*SWAPS_PER_UNIT
    cap=max(20,target*10)
    accepted=0; attempts=0
    while accepted<target and attempts<cap:
        attempts+=1
        i,j=rng.choice(len(pairs),size=2,replace=False)
        a,b,wab,wba=pairs[int(i)]; c,d,wcd,wdc=pairs[int(j)]
        old={(a,b),(b,a),(c,d),(d,c)}
        present.difference_update(old)
        for x in old: weights.pop(x)
        new={(a,d),(d,a),(c,b),(b,c)}
        valid=(len({a,b,c,d})==4 and len(new)==4 and new!=old and not (new&present))
        if valid:
            present.update(new)
            weights[(a,d)]=wab; weights[(d,a)]=wba
            weights[(c,b)]=wcd; weights[(b,c)]=wdc
            pairs[int(i)]=[a,d,wab,wba]; pairs[int(j)]=[c,b,wcd,wdc]
            accepted+=1
        else:
            present.update(old)
            weights[(a,b)]=wab; weights[(b,a)]=wba
            weights[(c,d)]=wcd; weights[(d,c)]=wdc
    return {"units":len(pairs),"target_swaps":target,"accepted_swaps":accepted,"attempts":attempts,"complete":accepted==target}

def weighted_global_null(src,dst,w,labels,seed):
    source_edges=edge_set(src,dst)
    rng=np.random.default_rng([WEIGHT_STREAM,int(seed)])
    permuted=np.asarray(rng.permutation(np.asarray(w,dtype=np.float32)),dtype=np.float32)
    n=int(max(src.max(),dst.max())+1)
    W=observed_matrix(src,dst,permuted,n)
    details={"edge_set_preserved":True,"weight_multiset_preserved":bool(np.array_equal(np.sort(np.asarray(w,dtype=np.float32)),np.sort(permuted))),"original_reciprocal_pairs":reciprocal_count(source_edges),"reciprocal_pairs":reciprocal_count(source_edges),"block_counts_preserved":True,"source_units":{"edge_records":len(src)}}
    if not details["weight_multiset_preserved"]:
        raise RuntimeError("weight permutation multiset invariant failed")
    return W,details,src.copy(),dst.copy(),permuted

def observed_matrix(src,dst,w,n):
    return sparse.csr_matrix((w,(dst,src)),shape=(n,n))

def run_seed(g,nodes,degree,labels,streams,src,dst,w,seed,trials,smoke,outdir):
    started=time.perf_counter()
    W_obs=observed_matrix(src,dst,w,len(nodes))
    W_null,nd,ns,nt,nw=weighted_global_null(src,dst,w,labels,seed)
    W_pos=R.positive_graph(len(nodes),streams,len(src),seed)
    pos=R.run_arm(W_pos,"positive_control",streams,seed,trials,do_metrics=True,smoke=smoke)
    pos_pass=(pos.get("status")=="MEASURED" and (smoke or pos.get("metrics",{}).get("routing_margin",-1.0)>=R.MIN_ROUTING_MARGIN))
    row={"seed":int(seed),"selected_labels":streams["selected_labels"],"source_edges":int(len(src)),"source_reciprocal_pairs":reciprocal_count(edge_set(src,dst)),"permutation_diagnostics":nd,"positive_control":pos,"positive_control_pass":bool(pos_pass),"arms":{}}
    if not pos_pass:
        row["status"]="SMOKE_POSITIVE_LIVENESS_FAILED" if smoke else "INVALIDATED"
    else:
        for name,W in (("observed_signed",W_obs),("weight_permuted",W_null)):
            row["arms"][name]=R.run_arm(W,name,streams,seed,trials,do_metrics=True,smoke=smoke)
        row["status"]="SMOKE_MEASURED_NOT_EVIDENCE" if smoke else "MEASURED"
    row["elapsed_seconds"]=round(time.perf_counter()-started,3)
    R.write_json_once(outdir/("seed-%02d.json"%seed),row)
    return row

def aggregate(rows,smoke):
    if smoke:
        return {"classification":"SMOKE_NOT_EVIDENCE","seeds_completed":len(rows),"positive_control_live":[bool(x.get("positive_control_pass")) for x in rows]}
    pos=all(bool(x.get("positive_control_pass")) for x in rows) and len(rows)==len(R.SEEDS)
    arms=("observed_signed","weight_permuted")
    measured={}
    for name in arms:
        measured[name]=[x["arms"][name] for x in rows if name in x.get("arms",{}) and x["arms"][name].get("status")=="MEASURED" and "metrics" in x["arms"][name]]
    common=[x for x in rows if all(name in x.get("arms",{}) and x["arms"][name].get("status")=="MEASURED" and "metrics" in x["arms"][name] for name in arms)]
    diffs=np.asarray([x["arms"]["observed_signed"]["metrics"]["routing_margin"]-x["arms"]["weight_permuted"]["metrics"]["routing_margin"] for x in common],dtype=np.float64)
    paired={"n":int(len(diffs)),"values":diffs.tolist(),"mean":float(diffs.mean()) if len(diffs) else None,"sd":float(diffs.std(ddof=1)) if len(diffs)>1 else None,"ci95":None}
    if len(diffs)>1:
        half=float(R.student_t.ppf(0.975,len(diffs)-1)*diffs.std(ddof=1)/np.sqrt(len(diffs)))
        paired["ci95"]=[float(diffs.mean()-half),float(diffs.mean()+half)]
    if pos and len(diffs)>=MIN_PAIRED_SEEDS and paired["ci95"] and paired["ci95"][0]>0:
        classification="PASS_OBSERVED_OVER_NULL"
    elif pos and len(diffs)>=MIN_PAIRED_SEEDS and paired["ci95"] and paired["ci95"][1]<0:
        classification="PASS_NULL_OVER_OBSERVED"
    else:
        classification="INCONCLUSIVE"
    return {"classification":classification,"positive_control_all_pass":bool(pos),"arms":{name:{"n_measured":len(v),"missing_seeds":[int(s) for s in R.SEEDS if s not in {int(x["seed"]) for x in v}]} for name,v in measured.items()},"paired_primary":paired}

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--smoke",action="store_true"); args=ap.parse_args()
    smoke=bool(args.smoke); seeds=R.SMOKE_SEEDS if smoke else R.SEEDS
    trials=R.SMOKE_TRIALS_PER_PATTERN if smoke else R.N_TRIALS_PER_PATTERN
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outroot=ROOT/"research"/"results"/"MOTIF-FUNC-002"; outdir=outroot/(( "SMOKE_" if smoke else "FULL_")+stamp+"_"+R.git_rev()[:12]); outdir.mkdir(parents=True)
    protocol=ROOT/"research/MOTIF-FUNC-002-PROTOCOL.md"
    g=R.load_graph(load_neurons=False); nodes,degree=R.choose_nodes(g); labels=R.load_superclasses(); streams=R.choose_streams(nodes,degree,labels)
    src,dst,w=weighted_edges(g,nodes)
    meta={"experiment":"MOTIF-FUNC-002","mode":"smoke" if smoke else "full","status":"RUNNING","git_tip":R.git_rev(),"protocol_sha256":R.sha256_file(protocol),"runner_sha256":R.sha256_file(ROOT/"research/motif_func_002.py"),"selected_nodes":nodes.tolist(),"selected_labels":streams["selected_labels"],"source_edge_records":int(len(src)),"source_self_loops_removed":4,"source_reciprocal_pairs":reciprocal_count(edge_set(src,dst)),"raw_and_derived_graph_untouched":True,"route_constants_imported":"research/routing_003.py"}
    R.write_json_once(outdir/"metadata.json",meta)
    rows=[]
    for seed in seeds:
        print("seed",int(seed),flush=True)
        rows.append(run_seed(g,nodes,degree,labels,streams,src,dst,w,int(seed),trials,smoke,outdir))
    summary={"experiment":"MOTIF-FUNC-002","mode":meta["mode"],"classification":"SMOKE_NOT_EVIDENCE" if smoke else "FUNCTIONAL_MEASURED","seeds_completed":[int(x["seed"]) for x in rows],"aggregate":aggregate(rows,smoke),"claim_scope":"locked LIF readout comparison only; no biology, general topology, novelty, or ML transfer","protocol_sha256":meta["protocol_sha256"],"runner_sha256":meta["runner_sha256"]}
    R.write_json_once(outdir/"summary.json",summary); print(json.dumps(summary,indent=2,sort_keys=True),flush=True); print("WROTE",outdir/"summary.json",flush=True)
if __name__=="__main__": main()
