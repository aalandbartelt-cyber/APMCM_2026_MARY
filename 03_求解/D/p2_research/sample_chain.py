"""Local exploratory SDK SA, fixed 100 restarts, raw returns retained."""
from pathlib import Path
import os,sys,json,time,hashlib,datetime
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[3]

def main():
    file=ROOT/'artifacts/p2_research_20261128/domain_wall/DW01_11_joint.npz'
    dest=file.parent/'SA_DW01_100';dest.mkdir(exist_ok=False)
    z=np.load(file);K=z['J'];values=z['values'];mapping=z['mapping']
    scale=float(4*np.abs(K).sum(axis=1).max())
    cfg=dict(experiment='SA_DW01_100',matrix_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        restarts=100,seeds=[260001,260100],initial_temperature=scale,
        cutoff_temperature=scale*1e-4,alpha=.99,iterations_per_t=10,size_limit=1,process_num=1,
        repair=False,framework='exploratory research; no hardware or confirmatory selection')
    (dest/'registration.json').write_text(json.dumps(cfg,indent=2))
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'))
    from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def forbidden(*args,**kwargs):raise RuntimeError('Network prohibited during local SA')
    requests.sessions.Session.request=forbidden
    rows=[];started=time.monotonic()
    with (dest/'raw.jsonl').open('x') as f:
        for index in range(100):
            seed=260001+index;row=dict(index=index,seed=seed)
            try:
                solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=scale,
                    cutoff_temperature=scale*1e-4,alpha=.99,iterations_per_t=10,size_limit=1,
                    rand_seed=seed,process_num=1)
                output=np.asarray(solver.solve(K));assert output.shape==(1,len(K)) and np.isin(output,[-1,1]).all()
                s=output[0].astype(np.int64);x=(s[:-1]*s[-1]+1)//2
                violations=int(np.sum((x[1:]==1)&(x[:-1]==0)));feasible=violations==0
                position=int(x.sum()) if feasible else None
                candidate=int(mapping[position]) if feasible else None
                row.update(status='VALID_COMPLETED',spins=s.tolist(),energy=int(-s@K@s),
                    violations=violations,feasible=feasible,candidate=candidate,
                    regret=float(values[candidate]-values.min()) if feasible else None)
            except Exception as e:row.update(status='FAILED',error_type=type(e).__name__,error=str(e)[:300])
            rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
            if (index+1)%10==0:print(json.dumps(dict(done=index+1,feasible=sum(r.get('feasible',False) for r in rows),seconds=time.monotonic()-started)),flush=True)
    feasible=[r for r in rows if r.get('feasible')]
    summary=dict(attempted=100,valid=sum(r['status']=='VALID_COMPLETED' for r in rows),feasible=len(feasible),
        ground_hits=sum(r['regret']==0 for r in feasible),near2_hits=sum(r['regret']<=2 for r in feasible),
        conditional_regret_quantiles=np.quantile([r['regret'] for r in feasible],[0,.5,.9,1]).tolist() if feasible else None,
        selected_by_energy=min(feasible,key=lambda r:(r['energy'],r['candidate'],r['index']))['index'] if feasible else None,
        elapsed_seconds=time.monotonic()-started)
    (dest/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
