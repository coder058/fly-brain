#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy import sparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research import motif_mine_005 as BASE

# SOURCE: MOTIF-MINE-006 protocol, fixed subgraph.
N_NULLS=20
SEEDS=tuple(range(N_NULLS))
# SOURCE: smoke is one draw and cannot be evidence.
SMOKE_SEEDS=(0,)
# SOURCE: MOTIF-MINE-006 protocol, accepted swaps per unit.
SWAPS_PER_UNIT=20

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

def reciprocity_block_null(A,labels,seed):
    rng=np.random.default_rng([60606,int(seed)])
    present=edge_set(A)
    original_edges=set(present)
    pair_seen=set()
    pairs=[]
    singles=[]
    for a,b in sorted(present):
        if (a,b) in pair_seen:
            continue
        if (b,a) in present and a!=b:
            x,y=orient_pair(a,b,labels)
            pairs.append([x,y])
            pair_seen.add((a,b)); pair_seen.add((b,a))
        else:
            singles.append([a,b])
    single_groups=defaultdict(list)
    for i,(a,b) in enumerate(singles):
        single_groups[(str(labels[a]),str(labels[b]))].append(i)
    pair_groups=defaultdict(list)
    for i,(a,b) in enumerate(pairs):
        pair_groups[(str(labels[a]),str(labels[b]))].append(i)
    reports={"single":{},"reciprocal":{}}
    accepted_total=0
    attempts_total=0

    for key,idxs in sorted(single_groups.items()):
        target=len(idxs)*SWAPS_PER_UNIT
        accepted=0; attempts=0
        cap=max(20,target*10)
        while accepted<target and attempts<cap and len(idxs)>1:
            attempts+=1
            i,j=rng.choice(idxs,size=2,replace=False)
            a,b=singles[int(i)]; c,d=singles[int(j)]
            old=((a,b),(c,d)); new=((a,d),(c,b))
            remaining=present-{old[0],old[1]}
            if a==d or c==b or new[0] in remaining or new[1] in remaining:
                continue
            if any((b0,a0) in remaining for a0,b0 in new):
                continue
            present.discard(old[0]); present.discard(old[1])
            present.add(new[0]); present.add(new[1])
            singles[int(i)]=[a,d]; singles[int(j)]=[c,b]
            accepted+=1
        accepted_total+=accepted; attempts_total+=attempts
        reports["single"]["|".join(key)]={"units":len(idxs),"accepted_swaps":accepted,"target_swaps":target,"attempts":attempts}

    for key,idxs in sorted(pair_groups.items()):
        target=len(idxs)*SWAPS_PER_UNIT
        accepted=0; attempts=0
        cap=max(20,target*10)
        while accepted<target and attempts<cap and len(idxs)>1:
            attempts+=1
            i,j=rng.choice(idxs,size=2,replace=False)
            a,b=pairs[int(i)]; c,d=pairs[int(j)]
            if len({a,b,c,d})<4:
                continue
            new=((a,d),(d,a),(c,b),(b,c))
            if any(x in present for x in new):
                continue
            present.discard((a,b)); present.discard((b,a))
            present.discard((c,d)); present.discard((d,c))
            present.update(new)
            pairs[int(i)]=[a,d]; pairs[int(j)]=[c,b]
            accepted+=1
        accepted_total+=accepted; attempts_total+=attempts
        reports["reciprocal"]["|".join(key)]={"units":len(idxs),"accepted_swaps":accepted,"target_swaps":target,"attempts":attempts}

    if len(present)!=len(original_edges):
        raise RuntimeError("edge count changed during reciprocity null")
    dst=np.fromiter((b for a,b in sorted(present)),dtype=np.int64)
    src=np.fromiter((a for a,b in sorted(present)),dtype=np.int64)
    N=sparse.csr_matrix((np.ones(len(src),dtype=np.int8),(dst,src)),shape=A.shape)
    diag=BASE.graph_diag(N)
    details={"accepted_swaps":int(accepted_total),"attempts":int(attempts_total),"groups":reports,
             "source_units":{"single":len(singles),"reciprocal_pairs":len(pairs)},
             "reciprocal_pairs":reciprocal_count(present),
             "original_reciprocal_pairs":reciprocal_count(original_edges),
             "block_counts_preserved":block_counts(present,labels)==block_counts(original_edges,labels)}
    return N,details

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--smoke",action="store_true")
    args=ap.parse_args()
    smoke=bool(args.smoke)
    seeds=SMOKE_SEEDS if smoke else SEEDS
    stamp=BASE.datetime.now(BASE.timezone.utc).strftime("%Y%m%dT%H%M%SZ") if hasattr(BASE,"datetime") else __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outroot=ROOT/"research"/"results"/"MOTIF-MINE-006"
    outdir=outroot/(( "SMOKE_" if smoke else "FULL_")+stamp+"_"+BASE.git_rev()[:12])
    outdir.mkdir(parents=True)
    protocol=ROOT/"research/MOTIF-MINE-006-PROTOCOL.md"
    g=BASE.DEG.load_graph(load_neurons=False)
    nodes=BASE.choose_nodes(g)
    A,source_self_loops=BASE.unsigned_local(g,nodes)
    labels=BASE.BLOCK.load_labels()[nodes]
    od=BASE.graph_diag(A)
    obs=BASE.count_motifs(A)
    original=edge_set(A)
    meta={"experiment":"MOTIF-MINE-006","mode":"smoke" if smoke else "full","status":"RUNNING","git_tip":BASE.git_rev(),"protocol_sha256":BASE.sha256_file(protocol),"runner_sha256":BASE.sha256_file(ROOT/"research/motif_mine_006.py"),"selected_nodes":nodes.tolist(),"source_self_loops_removed":int(source_self_loops),"source_reciprocal_pairs":reciprocal_count(original),"graph_diag":od,"raw_and_derived_graph_untouched":True}
    BASE.write_once(outdir/"metadata.json",meta)
    BASE.write_once(outdir/"observed.json",{"motifs":obs,"graph_diag":od,"source_self_loops_removed":source_self_loops})
    print(json.dumps({"outdir":str(outdir),"mode":meta["mode"],"graph":{"n_nodes":od["n_nodes"],"n_edges":od["n_edges"]},"observed":obs,"seeds":[int(x) for x in seeds]}),flush=True)
    draws=[]
    for seed in seeds:
        print("seed",int(seed),flush=True)
        N,rd=reciprocity_block_null(A,labels,int(seed))
        nd=BASE.graph_diag(N)
        invariant=(nd["n_edges"]==od["n_edges"] and nd["self_loops"]==0 and nd["duplicate_edges"]==0 and nd["in_degree"]==od["in_degree"] and nd["out_degree"]==od["out_degree"] and rd["block_counts_preserved"] and rd["reciprocal_pairs"]==rd["original_reciprocal_pairs"])
        if not invariant:
            raise RuntimeError("reciprocity-block null invariant failed")
        dc=BASE.count_motifs(N)
        BASE.write_once(outdir/("null-%02d.json"%seed),{"seed":int(seed),"counts":dc,"graph_diag":nd,"rewire_diag":rd})
        draws.append(dc)
    summary={"experiment":"MOTIF-MINE-006","mode":meta["mode"],"classification":"SMOKE_NOT_EVIDENCE" if smoke else "STRUCTURAL_MEASURED","observed":obs,"null_draws":draws,"seeds_completed":[int(x) for x in seeds],"graph_diag":od,"source_self_loops_removed":int(source_self_loops),"source_reciprocal_pairs":reciprocal_count(original),"comparison":BASE.compare(obs,draws),"claim_scope":"reciprocity-preserving structural control only; no function, biology, novelty, or ML transfer"}
    BASE.write_once(outdir/"summary.json",summary)
    print(json.dumps(summary,indent=2,sort_keys=True),flush=True)
    print("WROTE",outdir/"summary.json",flush=True)
if __name__=="__main__":
    main()
