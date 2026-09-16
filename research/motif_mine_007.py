#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import sparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research import motif_mine_005 as BASE

# SOURCE: MOTIF-MINE-007 protocol.
N_NULLS=20
SEEDS=tuple(range(N_NULLS))
# SOURCE: smoke is one seed and cannot be evidence.
SMOKE_SEEDS=(0,)
# SOURCE: MOTIF-MINE-007 protocol, accepted permutation rounds per group.
ROUNDS_PER_GROUP=20
# SOURCE: MOTIF-MINE-007 protocol, attempts allowed for each round.
MAX_ATTEMPTS_PER_ROUND=200

def orient_pair(a,b,labels):
    la,lb=str(labels[a]),str(labels[b])
    return (a,b) if la<=lb else (b,a)

def edge_set(A):
    dst,src=A.nonzero()
    return {(int(a),int(b)) for a,b in zip(src,dst)}

def reciprocal_count(edges):
    return int(sum(1 for a,b in edges if (b,a) in edges)//2)

def block_counts(edges,labels):
    out=defaultdict(int)
    for a,b in edges:
        out[(str(labels[a]),str(labels[b]))]+=1
    return dict(sorted(out.items()))

def split_units(edges,labels):
    seen=set()
    singles=[]
    pairs=[]
    for a,b in sorted(edges):
        if (a,b) in seen:
            continue
        if a!=b and (b,a) in edges:
            x,y=orient_pair(a,b,labels)
            pairs.append([x,y])
            seen.add((a,b)); seen.add((b,a))
        else:
            singles.append([a,b])
            seen.add((a,b))
    return singles,pairs

def _rotations(values,rng):
    n=len(values)
    if n==0:
        return
    base=[int(x) for x in rng.permutation(values)]
    if n==1:
        yield base
        return
    trials=min(MAX_ATTEMPTS_PER_ROUND,n-1)
    offsets=rng.choice(np.arange(1,n,dtype=np.int64),size=trials,replace=False)
    for shift in offsets:
        yield [base[(j+int(shift))%n] for j in range(n)]

def _single_candidate(others,sources,perm):
    new=[(int(a),int(b)) for a,b in zip(sources,perm)]
    newset=set(new)
    if any(a==b for a,b in new):
        return None
    if len(newset)!=len(new) or newset & others:
        return None
    if any((b,a) in others or (b,a) in newset for a,b in new):
        return None
    return newset

def permute_single_group(present,singles,idxs,rng):
    reports={"units":len(idxs),"rounds":0,"nontrivial_rounds":0,"rigid_rounds":0,"attempts":0}
    sources=[singles[i][0] for i in idxs]
    destinations=[singles[i][1] for i in idxs]
    oldset={(a,b) for a,b in zip(sources,destinations)}
    present.difference_update(oldset)
    for _ in range(ROUNDS_PER_GROUP):
        accepted=False
        for perm in _rotations(destinations,rng):
            reports["attempts"]+=1
            newset=_single_candidate(present,sources,perm)
            if newset is None:
                continue
            present.update(newset)
            if list(perm)!=destinations:
                reports["nontrivial_rounds"]+=1
            for k,i in enumerate(idxs):
                singles[i]=[sources[k],int(perm[k])]
            oldset=newset
            destinations=[singles[i][1] for i in idxs]
            present.difference_update(oldset)
            reports["rounds"]+=1
            accepted=True
            break
        if not accepted:
            reports["rigid_rounds"]+=1
            reports["rounds"]+=1
    present.update(oldset)
    return reports

def _pair_candidate(others,sources,perm):
    new=[]
    for a,b in zip(sources,perm):
        a=int(a); b=int(b)
        new.extend(((a,b),(b,a)))
    newset=set(new)
    if any(a==b for a,b in new) or len(newset)!=len(new):
        return None
    if newset & others:
        return None
    return newset

def permute_pair_group(present,pairs,idxs,rng):
    reports={"units":len(idxs),"rounds":0,"nontrivial_rounds":0,"rigid_rounds":0,"attempts":0}
    sources=[pairs[i][0] for i in idxs]
    partners=[pairs[i][1] for i in idxs]
    oldset={(a,b) for a,b in zip(sources,partners)}
    oldset |= {(b,a) for a,b in zip(sources,partners)}
    present.difference_update(oldset)
    for _ in range(ROUNDS_PER_GROUP):
        accepted=False
        for perm in _rotations(partners,rng):
            reports["attempts"]+=1
            newset=_pair_candidate(present,sources,perm)
            if newset is None:
                continue
            present.update(newset)
            if list(perm)!=partners:
                reports["nontrivial_rounds"]+=1
            for k,i in enumerate(idxs):
                pairs[i]=[sources[k],int(perm[k])]
            oldset=newset
            partners=[pairs[i][1] for i in idxs]
            present.difference_update(oldset)
            reports["rounds"]+=1
            accepted=True
            break
        if not accepted:
            reports["rigid_rounds"]+=1
            reports["rounds"]+=1
    present.update(oldset)
    return reports

def reciprocity_endpoint_null(A,labels,seed):
    rng=np.random.default_rng([60607,int(seed)])
    original=edge_set(A)
    present=set(original)
    singles,pairs=split_units(original,labels)
    # SOURCE: M7 intentionally drops block preservation to obtain a mixed null.
    sg={("ALL",):list(range(len(singles)))}
    pg={("ALL",):list(range(len(pairs)))}
    reports={"single":{},"reciprocal":{}}
    for key,idxs in sorted(sg.items()):
        reports["single"]["|".join(key)]=permute_single_group(present,singles,idxs,rng)
    for key,idxs in sorted(pg.items()):
        reports["reciprocal"]["|".join(key)]=permute_pair_group(present,pairs,idxs,rng)
    if len(present)!=len(original):
        raise RuntimeError("edge count changed in endpoint null")
    ordered=sorted(present)
    src=np.asarray([a for a,b in ordered],dtype=np.int64)
    dst=np.asarray([b for a,b in ordered],dtype=np.int64)
    N=sparse.csr_matrix((np.ones(len(src),dtype=np.int8),(dst,src)),shape=A.shape)
    details={"groups":reports,"source_units":{"single":len(singles),"reciprocal_pairs":len(pairs)},"original_reciprocal_pairs":reciprocal_count(original),"reciprocal_pairs":reciprocal_count(present),"block_counts_preserved":block_counts(present,labels)==block_counts(original,labels)}
    return N,details

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--smoke",action="store_true")
    args=ap.parse_args()
    smoke=bool(args.smoke)
    seeds=SMOKE_SEEDS if smoke else SEEDS
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outroot=ROOT/"research"/"results"/"MOTIF-MINE-007"
    outdir=outroot/(( "SMOKE_" if smoke else "FULL_")+stamp+"_"+BASE.git_rev()[:12])
    outdir.mkdir(parents=True)
    protocol=ROOT/"research/MOTIF-MINE-007-PROTOCOL.md"
    g=BASE.DEG.load_graph(load_neurons=False)
    nodes=BASE.choose_nodes(g)
    A,source_self_loops=BASE.unsigned_local(g,nodes)
    labels=BASE.BLOCK.load_labels()[nodes]
    od=BASE.graph_diag(A)
    obs=BASE.count_motifs(A)
    original=edge_set(A)
    meta={"experiment":"MOTIF-MINE-007","mode":"smoke" if smoke else "full","status":"RUNNING","git_tip":BASE.git_rev(),"protocol_sha256":BASE.sha256_file(protocol),"runner_sha256":BASE.sha256_file(ROOT/"research/motif_mine_006b.py"),"selected_nodes":nodes.tolist(),"source_self_loops_removed":int(source_self_loops),"source_reciprocal_pairs":reciprocal_count(original),"graph_diag":od,"raw_and_derived_graph_untouched":True}
    BASE.write_once(outdir/"metadata.json",meta)
    BASE.write_once(outdir/"observed.json",{"motifs":obs,"graph_diag":od,"source_self_loops_removed":source_self_loops})
    print(json.dumps({"outdir":str(outdir),"mode":meta["mode"],"graph":{"n_nodes":od["n_nodes"],"n_edges":od["n_edges"]},"observed":obs,"seeds":[int(x) for x in seeds]}),flush=True)
    draws=[]
    for seed in seeds:
        print("seed",int(seed),flush=True)
        N,rd=reciprocity_endpoint_null(A,labels,int(seed))
        nd=BASE.graph_diag(N)
        invariant=(nd["n_edges"]==od["n_edges"] and nd["self_loops"]==0 and nd["duplicate_edges"]==0 and nd["in_degree"]==od["in_degree"] and nd["out_degree"]==od["out_degree"] and rd["reciprocal_pairs"]==rd["original_reciprocal_pairs"])
        if not invariant:
            raise RuntimeError("endpoint reciprocity null invariant failed")
        dc=BASE.count_motifs(N)
        BASE.write_once(outdir/("null-%02d.json"%seed),{"seed":int(seed),"counts":dc,"graph_diag":nd,"rewire_diag":rd})
        draws.append(dc)
    summary={"experiment":"MOTIF-MINE-007","mode":meta["mode"],"classification":"SMOKE_NOT_EVIDENCE" if smoke else "STRUCTURAL_MEASURED","observed":obs,"null_draws":draws,"seeds_completed":[int(x) for x in seeds],"graph_diag":od,"source_self_loops_removed":int(source_self_loops),"source_reciprocal_pairs":reciprocal_count(original),"comparison":BASE.compare(obs,draws),"claim_scope":"efficient reciprocity-preserving structural control only; no function, biology, novelty, or ML transfer"}
    BASE.write_once(outdir/"summary.json",summary)
    print(json.dumps(summary,indent=2,sort_keys=True),flush=True)
    print("WROTE",outdir/"summary.json",flush=True)
if __name__=="__main__":
    main()
