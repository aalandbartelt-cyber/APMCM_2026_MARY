"""Pre-registered independent SA restarts. Never selects hardware representations."""
import argparse
import concurrent.futures
import json
import os
import sys
import time
import numpy as np
from p2_common import ROOT,OUT,REG,anchor,write_new,append,now,tie

def initialize_license():
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'))
    from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)

def decode(J,mask,W,keys,s):
    n=mask.shape[0];x=((s[:-1]*s[-1]+1)//2).astype(np.int64)
    a=x[:n];b=x[n:];one=bool(a.sum()==1 and b.sum()==1)
    allowed=one and bool(mask[a.argmax(),b.argmax()]);best=float(W[mask].min())
    result=dict(a_onehot=bool(a.sum()==1),b_onehot=bool(b.sum()==1),feasible=allowed,
        energy=float(-s@J@s),key=str(keys[a.argmax(),b.argmax()]) if one else None,
        regret=float(W[a.argmax(),b.argmax()]-best) if allowed else None)
    # Distance to each legal pair: sum(x)+2-2*(a_i+b_j). Independent of W.
    pairs=np.argwhere(mask);score=a[pairs[:,0]]+b[pairs[:,1]];bestscore=score.max()
    pairs=pairs[score==bestscore];i,j=min(pairs.tolist(),key=lambda ij:tie(keys[tuple(ij)]))
    result.update(repaired_key=str(keys[i,j]),repaired_regret=float(W[i,j]-best),repair_distance=int(x.sum()+2-2*bestscore))
    return result

def block_job(job):
    import kaiwu as kw
    ident,file,temp,block,mode=job;path=OUT/'sa'/f'{ident}_{temp}_{mode}_{block:02d}.json'
    if path.exists():return dict(id=ident,temperature=temp,block=block,cached=True)
    z=np.load(ROOT/file);J=z['J'];mask=z['allowed'];W=z['W'];keys=z['keys']
    scale=4*np.abs(J).sum(axis=1).max()
    initial,cutoff=(100.,.001) if temp=='fixed' else (float(scale),float(scale*1e-4))
    if scale==0:
        write_new(path,dict(id=ident,temperature=temp,block=block,status='DEGENERATE_ZERO_MATRIX',restarts=[]));return dict(id=ident,status='DEGENERATE')
    records=[];start=time.monotonic();r=0
    while r<100 if mode=='count' else time.monotonic()-start<60:
        seed=230026+100*block+r if mode=='count' else 250026+100000*block+r
        begun=time.monotonic();row=dict(restart=r,seed=seed)
        try:
            solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=initial,cutoff_temperature=cutoff,alpha=.99,iterations_per_t=10,size_limit=1,rand_seed=seed,process_num=1)
            returned=np.asarray(solver.solve(J),dtype=np.int64)
            solve_seconds=time.monotonic()-begun
            assert returned.shape==(1,len(J)) and np.isin(returned,[-1,1]).all()
            decoded=decode(J,mask,W,keys,returned[0]);done=time.monotonic()
            # Wall-clock samples completing beyond the 60s window are archived but not included.
            row.update(status='VALID_COMPLETED',spins=returned[0].tolist(),solve_seconds=solve_seconds,
                decode_repair_seconds=done-begun-solve_seconds,completed_at_seconds=done-start,
                within_window=mode=='count' or done-start<=60,**decoded)
        except Exception as exc:
            row.update(status='COMPUTATION_FAILED',error=type(exc).__name__,seconds=time.monotonic()-begun)
        records.append(row);r+=1
    write_new(path,dict(id=ident,temperature=temp,mode=mode,block=block,initial_temperature=initial,cutoff_temperature=cutoff,
        elapsed_seconds=time.monotonic()-start,restarts=records,status='COMPLETE'))
    return dict(id=ident,temperature=temp,block=block,restarts=len(records),seconds=time.monotonic()-start)

def main():
    p=argparse.ArgumentParser();p.add_argument('--anchor-commit',required=True);args=p.parse_args()
    receipt=anchor(args.anchor_commit);(OUT/'sa').mkdir(exist_ok=True)
    jobs=[]
    for row in receipt['sa_matrices']:
        for temp in ('scaled','fixed'):
            for block in range(20):jobs.append((row['id'],row['matrix_file'],temp,block,'count'))
    if receipt['selected']:
        row=next(r for r in receipt['configurations'] if r['id']==receipt['selected'])
        jobs.extend((row['id'],row['matrix_file'],'scaled',b,'wall60') for b in range(20))
    write_new(OUT/'sa_started.json',dict(time=now(),anchor_commit=args.anchor_commit,jobs=len(jobs),predeclared_max_restarts=48000,workers=4))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,initializer=initialize_license) as pool:
        for result in pool.map(block_job,jobs):print(json.dumps(result),flush=True)
    print(json.dumps(dict(done=True)),flush=True)

if __name__=='__main__':main()
