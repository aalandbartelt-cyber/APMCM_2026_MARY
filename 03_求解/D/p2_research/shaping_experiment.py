"""H01: fixed monotone cost maps and independent domain-wall subproblems."""
from pathlib import Path
import os,sys,json,hashlib,time,datetime
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artifacts/p2_research_20261128/shaping_H01'
FAMILIES=['linear','piecewise2','sqrt','log2','capped_log8','rank_sqrt']

def make_q(regret,family):
    R=float(regret.max());u=regret/R
    if family=='linear':f=u
    elif family=='piecewise2':f=np.where(regret<=2,.75*regret/2,.75+.25*(regret-2)/(R-2))
    elif family=='sqrt':f=np.sqrt(u)
    elif family=='log2':f=np.log1p(regret/2)/np.log1p(R/2)
    elif family=='capped_log8':f=np.log1p(np.minimum(regret,8)/2)/np.log1p(4)
    elif family=='rank_sqrt':
        unique=np.unique(regret);r=np.searchsorted(unique,regret);f=np.sqrt(r/(len(unique)-1))
    else:raise ValueError(family)
    return np.rint(127*f).astype(np.int64)

def construct(q,groups,P=254):
    blocks=np.array_split(np.arange(len(q)),groups)
    n=sum(len(b)+1 for b in blocks);K=np.zeros((n+1,n+1),dtype=np.int64);meta=[];start=0
    for block in blocks:
        padded=np.r_[q[block[0]],q[block],q[block[-1]]];length=len(padded)-1
        mapping=np.r_[block[0],block,block[-1]]
        ids=np.arange(start,start+length-1);K[ids,ids+1]=K[ids+1,ids]=P//2
        h=-np.diff(padded);h[0]+=P//2;h[-1]-=P//2
        K[start:start+length,n]=K[n,start:start+length]=h
        meta.append(dict(start=start,stop=start+length,mapping=mapping.tolist(),q=padded.tolist()))
        start+=length
    assert n+1<=550 and np.abs(K).max()<=127
    return K,meta

def main():
    OUT.mkdir(exist_ok=False)
    source=ROOT/'artifacts/p23_v2/pool_11.npz';z=np.load(source)
    mask=z['allowed'][:,:,0];values=z['vhat'][:,:,0][mask];regret=values-values.min()
    registrations=dict(id='H01',time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        families=FAMILIES,groups=20,P=254,rounding='nearest-even integer; 127 levels',
        order='original row-major; array_split into 20 contiguous groups; no cost-based ordering',
        restarts_per_family=100,seeds='270001..270100 shared across families',
        initial_temperature='4 max absolute row sum',cutoff_ratio=.0001,alpha=.99,iterations_per_t=10,
        decoding='decode each chain separately; retain valid prefix chains; select lowest q then original index',
        metrics='all_chains_feasible and any_valid_chain separately; no repair; unconditional top20/ps; conditional ranks',
        claims='post-hoc exploratory decomposition; one hardware-like sample gives up to 20 subproblem candidates',
        hardware_calls=0,new_fits=0)
    (OUT/'registration.json').write_text(json.dumps(registrations,indent=2))
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'));from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def no_network(*a,**k):raise RuntimeError('Network prohibited during local SA')
    requests.sessions.Session.request=no_network
    summaries=[]
    for family in FAMILIES:
        folder=OUT/family;folder.mkdir();q=make_q(regret,family);K,blocks=construct(q,20)
        with (folder/'matrix.npz').open('xb') as f:np.savez_compressed(f,J=K,q=q,values=values)
        (folder/'blocks.json').write_text(json.dumps(blocks))
        scale=float(4*np.abs(K).sum(1).max());rows=[];start=time.monotonic()
        with (folder/'raw.jsonl').open('x') as f:
            for index in range(100):
                row=dict(index=index,seed=270001+index)
                try:
                    solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=scale,cutoff_temperature=scale*1e-4,
                        alpha=.99,iterations_per_t=10,size_limit=1,rand_seed=270001+index,process_num=1)
                    raw=np.asarray(solver.solve(K));assert raw.shape==(1,len(K)) and np.isin(raw,[-1,1]).all()
                    s=raw[0].astype(np.int64);x=(s[:-1]*s[-1]+1)//2;candidates=[];violations=[]
                    for b in blocks:
                        d=x[b['start']:b['stop']];v=int(np.sum(d[1:]>d[:-1]));violations.append(v)
                        if v==0:candidates.append(b['mapping'][int(d.sum())])
                    chosen=min(candidates,key=lambda c:(q[c],c)) if candidates else None
                    row.update(status='VALID_COMPLETED',spins=s.tolist(),energy=int(-s@K@s),
                        block_violations=violations,valid_blocks=len(candidates),all_chains_feasible=len(candidates)==20,
                        candidate=chosen,regret=float(regret[chosen]) if chosen is not None else None,
                        rank=int(1+np.sum(values<values[chosen])) if chosen is not None else None)
                except Exception as e:row.update(status='FAILED',error_type=type(e).__name__,error=str(e)[:200])
                rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
        delivered=[r for r in rows if r.get('candidate') is not None]
        best=min(delivered,key=lambda r:(q[r['candidate']],r['candidate'],r['index'])) if delivered else None
        summary=dict(family=family,spins=len(K),max_J=int(np.abs(K).max()),P=254,initial_temperature=scale,
            valid=sum(r['status']=='VALID_COMPLETED' for r in rows),attempted=100,
            all_chains_feasible=sum(r.get('all_chains_feasible',False) for r in rows),usable_samples=len(delivered),
            total_valid_blocks=sum(r.get('valid_blocks',0) for r in rows),median_rank=float(np.median([r['rank'] for r in delivered])) if delivered else None,
            top20_rate=sum(r['rank']<=20 for r in delivered)/100,ps=sum(r['regret']==0 for r in delivered)/100,
            near2_rate=sum(r['regret']<=2 for r in delivered)/100,
            conditional_regret_quantiles=np.quantile([r['regret'] for r in delivered],[0,.5,.9,1]).tolist() if delivered else None,
            best_100_regret=best['regret'] if best else None,ground_q_worst_regret=float(regret[q==q.min()].max()),
            integer_business_gap=int(np.unique(q)[1]-q.min()),elapsed_seconds=time.monotonic()-start)
        (folder/'summary.json').write_text(json.dumps(summary,indent=2));summaries.append(summary);print(json.dumps(summary),flush=True)
    (OUT/'summary.json').write_text(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
