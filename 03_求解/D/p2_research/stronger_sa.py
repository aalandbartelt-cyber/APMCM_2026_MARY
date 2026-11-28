"""H02: budget expansion after H01; fixed three settings, no hardware calls."""
from pathlib import Path
import os, sys, json, hashlib, datetime, time
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from shaping_experiment import construct, make_q

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artifacts/p2_research_20261128/shaping_H02'
SETTINGS=[('single_linear',1,'linear'),('packed_linear',20,'linear'),('packed_piecewise2',20,'piecewise2')]

def prepare():
    OUT.mkdir(exist_ok=False)
    source=ROOT/'artifacts/p23_v2/pool_11.npz';z=np.load(source)
    values=z['vhat'][:,:,0][z['allowed'][:,:,0]];regret=values-values.min()
    reg=dict(id='H02',time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        context='Exploratory budget expansion after observing H01; no confirmatory claim',
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        settings=SETTINGS,P=254,order='row-major allowed candidate order, contiguous partitions',
        seeds='280001..280100 common across settings; fresh optimizer each restart',
        restarts_per_setting=100,iterations_per_t=550,alpha=.99,cutoff_ratio=.0001,
        initial_temperature='4 max absolute row sum',size_limit=1,
        decoding='valid prefix per chain; select smallest q, original candidate index; no repair',
        mandatory_metrics=['all_chains_feasible','any_valid_chain','rank','original_regret'],
        hardware_calls=0,new_fits=0)
    for name,groups,family in SETTINGS:
        f=OUT/name;f.mkdir();q=make_q(regret,family);K,blocks=construct(q,groups,P=254)
        with (f/'matrix.npz').open('xb') as h:np.savez_compressed(h,J=K,q=q,values=values)
        (f/'blocks.json').write_text(json.dumps(blocks))
    (OUT/'registration.json').write_text(json.dumps(reg,indent=2))
    print('H02 inputs and schedule frozen',flush=True)

def run(name):
    assert name in [s[0] for s in SETTINGS]
    f=OUT/name;z=np.load(f/'matrix.npz');K=z['J'];q=z['q'];v=z['values'];r=v-v.min()
    blocks=json.loads((f/'blocks.json').read_text());scale=float(4*np.abs(K).sum(1).max())
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'))
    from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def no_network(*a,**k):raise RuntimeError('Network prohibited during local SA')
    requests.sessions.Session.request=no_network
    start=time.monotonic();rows=[]
    with (f/'raw.jsonl').open('x') as stream:
        for i in range(100):
            row=dict(index=i,seed=280001+i)
            try:
                solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=scale,cutoff_temperature=scale*1e-4,
                    alpha=.99,iterations_per_t=550,size_limit=1,rand_seed=280001+i,process_num=1)
                a=np.asarray(solver.solve(K));assert a.shape==(1,len(K)) and np.isin(a,[-1,1]).all()
                s=a[0].astype(np.int64);x=(s[:-1]*s[-1]+1)//2;c=[];violations=[]
                for b in blocks:
                    d=x[b['start']:b['stop']];bad=int(np.sum(d[1:]>d[:-1]));violations.append(bad)
                    if not bad:c.append(b['mapping'][int(d.sum())])
                chosen=min(c,key=lambda t:(q[t],t)) if c else None
                row.update(status='VALID_COMPLETED',spins=s.tolist(),energy=int(-s@K@s),
                    block_violations=violations,valid_blocks=len(c),all_chains_feasible=len(c)==len(blocks),
                    candidate=chosen,regret=float(r[chosen]) if chosen is not None else None,
                    rank=int(1+sum(v<v[chosen])) if chosen is not None else None)
            except Exception as exc:
                row.update(status='FAILED',error_type=type(exc).__name__,error=str(exc)[:200])
            rows.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
            if (i+1)%20==0:print(name,i+1,'attempts',round(time.monotonic()-start,2),'s',flush=True)
    good=[x for x in rows if x.get('candidate') is not None]
    summary=dict(setting=name,attempted=100,valid=sum(x['status']=='VALID_COMPLETED' for x in rows),
        all_chains_feasible=sum(x.get('all_chains_feasible',False) for x in rows),usable=len(good),
        valid_blocks=sum(x.get('valid_blocks',0) for x in rows),
        ps=sum(x['regret']==0 for x in good)/100,near2_rate=sum(x['regret']<=2 for x in good)/100,
        top20_rate=sum(x['rank']<=20 for x in good)/100,
        median_rank=float(np.median([x['rank'] for x in good])) if good else None,
        regret_quantiles=np.quantile([x['regret'] for x in good],[0,.5,.9,1]).tolist() if good else None,
        elapsed_seconds=time.monotonic()-start)
    (f/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    else:run(sys.argv[1])
