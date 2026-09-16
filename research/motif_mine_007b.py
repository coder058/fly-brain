#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import sparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research import motif_mine_005 as BASE

# SOURCE: MOTIF-MINE-007B protocol.
N_NULLS=20
SEEDS=tuple(range(N_NULLS))
# SOURCE: smoke is one seed and cannot be evidence.
SMOKE_SEEDS=(0,)
# SOURCE: MOTIF-MINE-007B protocol, accepted swaps per unit.
SWAPS_PER_UNIT=20
# SOURCE: MOTIF-MINE-007B protocol, bounded attempt multiplier.
ATTEMPT_MULTIPLIER=10

def edge_set(A):
    dst,src=A.nonzero()
    return {(int(a),int(b)) for a,b in zip(src,dst)}

def reciprocal_count(edges):
    return int(sum(1 for a,b in edges if (b,a) in edges)//2)

def block_counts(edges,labels):
    out={}
    for a,b in edges:
        k=(str(labels[a]),str(labels[b]))
        out[k]=out.get(k,0)+1
    return dict(sorted(out.items()))

def split_units(edges):
    seen=set(); singles=[]; pairs=[]
    for a,b in sorted(edges):
        if (a,b) in seen:
            continue
        if a!=b and (b,a) in edges:
            x,y=(a,b) if a<b else (b,a)
            pairs.append([x,y])
            seen.add((a,b)); seen.add((b,a))
        else:
            singles.append([a,b]); seen.add((a,b))
    return singles,pairs

def swap_single_units(present,singles,rng):
    target=len(singles)*SWAPS_PER_UNIT
    cap=max(20,target*ATTEMPT_MULTIPLIER)
    accepted=0; attempts=0
    while accepted<target and attempts<cap:
        attempts+=1
        i,j=rng.choice(len(singles),size=2,replace=False)
        a,b=singles[int(i)]; c,d=singles[int(j)]
        old={(a,b),(c,d)}
        present.difference_update(old)
        new={(a,d),(c,b)}
        valid=(a!=d and c!=b and len(new)==2 and new!=old and not (new&present) and not any((y,x) in present or (y,x) in new for x,y in new))
        if valid:
            present.update(new)
            singles[int(i)]=[a,d]; singles[int(j)]=[c,b]
            accepted+=1
        else:
            present.update(old)
    return {"units":len(singles),"target_swaps":target,"accepted_swaps":accepted,"attempts":attempts,"complete":accepted==target}

def swap_pair_units(present,pairs,rng):
    target=len(pairs)*SWAPS_PER_UNIT
    cap=max(20,target*ATTEMPT_MULTIPLIER)
    accepted=0; attempts=0
    while accepted<target and attempts<cap:
        attempts+=1
        i,j=rng.choice(len(pairs),size=2,replace=False)
        a,b=pairs[int(i)]; c,d=pairs[int(j)]
        old={(a,b),(b,a),(c,d),(d,c)}
        present.difference_update(old)
        new={(a,d),(d,a),(c,b),(b,c)}
        valid=(len({a,b,c,d})==4 and len(new)==4 and new!=old and not (new&present))
        if valid:
            present.update(new)
            pairs[int(i)]=[a,d]; pairs[int(j)]=[c,b]
            accepted+=1
        else:
            present.update(old)
    return {"units":len(pairs),"target_swaps":target,"accepted_swaps":accepted,"attempts":attempts,"complete":accepted==target}

def global_reciprocity_null(A,labels,seed):
    rng=np.random.default_rng([70707,int(seed)])
    original=edge_set(A); present=set(original)
    singles,pairs=split_units(original)
    sd=swap_single_units(present,singles,rng)
    pd=swap_pair_units(present,pairs,rng)
    details={"single":sd,"reciprocal":pd,"original_reciprocal_pairs":reciprocal_count(original),"reciprocal_pairs":reciprocal_count(present),"block_counts_preserved":block_counts(present,labels)==block_counts(original,labels),"source_units":{"single":len(singles),"reciprocal_pairs":len(pairs)}}
    ordered=sorted(present)
    src=np.asarray([a for a,b in ordered],dtype=np.int64)
    dst=np.asarray([b for a,b in ordered],dtype=np.int64)
    N=sparse.csr_matrix((np.ones(len(src),dtype=np.int8),(dst,src)),shape=A.shape)
    return N,details

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--smoke",action="store_true")
    args=ap.parse_args()
    smoke=bool(args.smoke); seeds=SMOKE_SEEDS if smoke else SEEDS
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outroot=ROOT/"research"/"results"/"MOTIF-MINE-007B"
    outdir=outroot/(( "SMOKE_" if smoke else "FULL_")+stamp+"_"+BASE.git_rev()[:12])
    outdir.mkdir(parents=True)
    protocol=ROOT/"research/MOTIF-MINE-007B-PROTOCOL.md"
    g=BASE.DEG.load_graph(load_neurons=False); nodes=BASE.choose_nodes(g)
    A,loops=BASE.unsigned_local(g,nodes); labels=BASE.BLOCK.load_labels()[nodes]
    od=BASE.graph_diag(A); obs=BASE.count_motifs(A); original=edge_set(A)
    meta={"experiment":"MOTIF-MINE-007B","mode":"smoke" if smoke else "full","status":"RUNNING","git_tip":BASE.git_rev(),"protocol_sha256":BASE.sha256_file(protocol),"runner_sha256":BASE.sha256_file(ROOT/"research/motif_mine_007b.py"),"selected_nodes":nodes.tolist(),"source_self_loops_removed":int(loops),"source_reciprocal_pairs":reciprocal_count(original),"graph_diag":od,"raw_and_derived_graph_untouched":True}
    BASE.write_once(outdir/"metadata.json",meta); BASE.write_once(outdir/"observed.json",{"motifs":obs,"graph_diag":od,"source_self_loops_removed":loops})
    print(json.dumps({"outdir":str(outdir),"mode":meta["mode"],"graph":{"n_nodes":od["n_nodes"],"n_edges":od["n_edges"]},"observed":obs,"seeds":[int(x) for x in seeds]}),flush=True)
    draws=[]
    for seed in seeds:
        print("seed",int(seed),flush=True)
        N,rd=global_reciprocity_null(A,labels,int(seed)); nd=BASE.graph_diag(N)
        invariant=(nd["n_edges"]==od["n_edges"] and nd["self_loops"]==0 and nd["duplicate_edges"]==0 and nd["in_degree"]==od["in_degree"] and nd["out_degree"]==od["out_degree"] and rd["reciprocal_pairs"]==rd["original_reciprocal_pairs"] and rd["single"]["complete"] and rd["reciprocal"]["complete"])
        if not invariant: raise RuntimeError("global degree+reciprocity null invariant or completeness failed")
        dc=BASE.count_motifs(N)
        BASE.write_once(outdir/("null-%02d.json"%seed),{"seed":int(seed),"counts":dc,"graph_diag":nd,"rewire_diag":rd}); draws.append(dc)
    summary={"experiment":"MOTIF-MINE-007B","mode":meta["mode"],"classification":"SMOKE_NOT_EVIDENCE" if smoke else "STRUCTURAL_MEASURED","observed":obs,"null_draws":draws,"seeds_completed":[int(x) for x in seeds],"graph_diag":od,"source_self_loops_removed":loops,"source_reciprocal_pairs":reciprocal_count(original),"comparison":BASE.compare(obs,draws),"claim_scope":"global degree+reciprocity structural control; blocks intentionally not preserved; no function, biology, novelty, or ML transfer"}
    BASE.write_once(outdir/"summary.json",summary); print(json.dumps(summary,indent=2,sort_keys=True),flush=True); print("WROTE",outdir/"summary.json",flush=True)
if __name__=="__main__":
    main()
