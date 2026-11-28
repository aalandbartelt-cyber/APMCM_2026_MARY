"""H04: fresh paired sample blocks for shaped matrix vs business-zero control."""
from pathlib import Path
import os,sys,json,hashlib,time,datetime
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/p2_research_20261128/negative_H04'

def prepare():
    OUT.mkdir(exist_ok=False);src=ROOT/'artifacts/p2_research_20261128/shaping_H02/packed_piecewise2'
    z=np.load(src/'matrix.npz');J=z['J'];q=z['q'];v=z['values'];blocks=json.loads((src/'blocks.json').read_text())
    zero=J.copy();zero[:-1,-1]=zero[-1,:-1]=0
    for b in blocks:
        zero[b['start'],-1]=zero[-1,b['start']]=127
        zero[b['stop']-1,-1]=zero[-1,b['stop']-1]=-127
    with (OUT/'matrices.npz').open('xb') as f:np.savez_compressed(f,real=J,zero=zero,q=q,values=v)
    (OUT/'blocks.json').write_text(json.dumps(blocks))
    (OUT/'registration.json').write_text(json.dumps(dict(id='H04',time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        context='Exploratory fresh-seed verification after H01-H03; no confirmatory test or hardware selection',
        settings=['real','zero'],blocks_per_setting=5,samples_per_block=100,seeds='330001..330500 common across settings',
        rounds_per_temperature=550,alpha=.99,initial_temperature=float(4*np.abs(J).sum(1).max()),cutoff_ratio=.0001,
        control='Remove only business cost differences; retain chain couplings and boundary reference couplings.',
        decoding='Both settings use the identical original shaped q to choose among valid chains; no repair.',
        main_metrics='Strict whole-matrix feasibility AND partial-subproblem extraction separately; all failed/empty blocks retained.',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_sha256=hashlib.sha256((src/'matrix.npz').read_bytes()).hexdigest(),
        hardware_calls=0,fits=0),indent=2))

def job(spec):
    setting,block=spec;folder=OUT/f'{setting}_{block:02d}';folder.mkdir(exist_ok=False)
    z=np.load(OUT/'matrices.npz');J=z[setting];q=z['q'];v=z['values'];r=v-v.min();scale=float(4*np.abs(z['real']).sum(1).max())
    meta=json.loads((OUT/'blocks.json').read_text())
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'));from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def no_network(*a,**k):raise RuntimeError('Network prohibited during local SA')
    requests.sessions.Session.request=no_network
    rows=[];start=time.monotonic()
    with (folder/'raw.jsonl').open('x') as f:
        for i in range(100):
            seed=330001+block*100+i;row=dict(index=i,seed=seed)
            try:
                solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=scale,cutoff_temperature=scale*1e-4,alpha=.99,
                    iterations_per_t=550,size_limit=1,rand_seed=seed,process_num=1)
                a=np.asarray(solver.solve(J));assert a.shape==(1,len(J)) and np.isin(a,[-1,1]).all();s=a[0].astype(np.int64)
                x=(s[:-1]*s[-1]+1)//2;c=[];viol=[]
                for b in meta:
                    d=x[b['start']:b['stop']];bad=int(sum(d[1:]>d[:-1]));viol.append(bad)
                    if not bad:c.append(b['mapping'][int(d.sum())])
                chosen=min(c,key=lambda t:(q[t],t)) if c else None
                row.update(status='VALID_COMPLETED',spins=s.tolist(),energy=int(-s@J@s),valid_blocks=len(c),
                    all_chains_feasible=len(c)==len(meta),block_violations=viol,candidate=chosen,
                    regret=float(r[chosen]) if chosen is not None else None,rank=int(1+sum(v<v[chosen])) if chosen is not None else None)
            except Exception as exc:row.update(status='FAILED',error=type(exc).__name__+': '+str(exc)[:200])
            rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
    good=[r for r in rows if r.get('candidate') is not None]
    best=min(good,key=lambda x:(q[x['candidate']],x['candidate'],x['index'])) if good else None
    summary=dict(setting=setting,block=block,attempted=100,valid=sum(r['status']=='VALID_COMPLETED' for r in rows),
        strict_feasible=sum(r.get('all_chains_feasible',False) for r in rows),usable=len(good),
        hits=sum(r['regret']==0 for r in good),strict_hits=sum(r['regret']==0 and r['all_chains_feasible'] for r in good),
        near2=sum(r['regret']<=2 for r in good),top20=sum(r['rank']<=20 for r in good),
        best_regret=best['regret'] if best else None,seconds=time.monotonic()-start)
    (folder/'summary.json').write_text(json.dumps(summary,indent=2));return summary

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':
        from concurrent.futures import ProcessPoolExecutor,as_completed
        specs=[(s,b) for b in range(5) for s in ['real','zero']];result=[]
        with ProcessPoolExecutor(4) as ex:
            for future in as_completed([ex.submit(job,s) for s in specs]):
                r=future.result();result.append(r);print(json.dumps(r),flush=True)
        with (OUT/'summary.json').open('x') as f:json.dump(result,f,indent=2)
