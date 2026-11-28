"""B01: bounded falsification/sample probe of raw var split, delta=.25."""
from pathlib import Path
import os,sys,json,hashlib,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/p2_research_20261128/split_SA_B01'

def main():
    OUT.mkdir(exist_ok=False)
    src=ROOT/'artifacts/p2_research_20261128/split_resolution/float_raw_var_0.25.npz';z=np.load(src)
    J=np.rint(z['J']/z['delta']).astype(np.int64);idx=z['indices'];starts=np.r_[0,idx[:-1]+1]
    pool=np.load(ROOT/'artifacts/p23_v2/pool_11.npz');v=pool['vhat'][:,:,0];mask=pool['allowed'][:,:,0];scale=float(4*np.abs(J).sum(1).max())
    (OUT/'registration.json').write_text(json.dumps(dict(id='B01',reason='raw delta.25 passed coherent G2 but full copy consistency is unproved',
        source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        restarts=100,seeds='310001..310100',alpha=.99,initial_temperature=scale,cutoff_ratio=.0001,iterations_per_t=550,
        no_repair=True,stop='all100 regardless of success; no hardware or fits'),indent=2))
    legal=[]
    for a,b in np.argwhere(mask):
        s=-np.ones(105,dtype=np.int64);s[a]=s[52+b]=s[-1]=1;t=np.repeat(s,idx+1-starts);legal.append(int(-t@J@t))
    legal_min=min(legal)
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'));from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def no_network(*a,**k):raise RuntimeError('Network prohibited during local SA')
    requests.sessions.Session.request=no_network
    rows=[];start=time.monotonic()
    with (OUT/'raw.jsonl').open('x') as f:
        for i in range(100):
            row=dict(index=i,seed=310001+i)
            try:
                solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=scale,cutoff_temperature=scale*1e-4,alpha=.99,
                    iterations_per_t=550,rand_seed=310001+i,size_limit=1,process_num=1)
                a=np.asarray(solver.solve(J));assert a.shape==(1,len(J)) and np.isin(a,[-1,1]).all();s=a[0].astype(np.int64)
                copy_ok=all(np.all(s[lo:hi+1]==s[hi]) for lo,hi in zip(starts,idx));t=s[idx]*s[idx[-1]];x=(t[:-1]+1)//2
                aa=np.flatnonzero(x[:52]);bb=np.flatnonzero(x[52:]);feasible=copy_ok and len(aa)==len(bb)==1 and bool(mask[aa[0],bb[0]])
                e=int(-s@J@s);row.update(status='VALID_COMPLETED',spins=s.tolist(),energy=e,copy_consistent=bool(copy_ok),
                    feasible=bool(feasible),regret=float(v[aa[0],bb[0]]-v[mask].min()) if feasible else None,
                    below_legal_coherent_min=e<legal_min,illegal_witness=e<=legal_min and not feasible)
            except Exception as exc:row.update(status='FAILED',error=type(exc).__name__+': '+str(exc)[:200])
            rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
            if (i+1)%25==0:print(i+1,'attempts',round(time.monotonic()-start,2),flush=True)
    good=[r for r in rows if r.get('feasible',False)]
    summary=dict(attempted=100,valid=sum(r['status']=='VALID_COMPLETED' for r in rows),coherent_legal_min=legal_min,
        copy_consistent=sum(r.get('copy_consistent',False) for r in rows),feasible=len(good),
        witnesses=sum(r.get('illegal_witness',False) for r in rows),ps=sum(r['regret']==0 for r in good)/100,
        conditional_regret_quantiles=np.quantile([r['regret'] for r in good],[0,.5,.9,1]).tolist() if good else None,
        seconds=time.monotonic()-start)
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
