"""Small exhaustive SDK API probes and bounded split size measurements (no fits/CIM)."""
from pathlib import Path
import os,sys,json,itertools,time,hashlib
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/p2_research_20261128/sdk_probes'

def states(n):return np.array(list(itertools.product([-1,1],repeat=n)),dtype=np.int64)
def energy(S,J):return -np.einsum('bi,ij,bj->b',S,J,S)

def main():
    OUT.mkdir(exist_ok=False)
    (OUT/'registration.json').write_text(json.dumps(dict(
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        mutate='5-spin SDK example; iterations=0 plus 4 heuristic/decision combinations once each',
        split='3-spin signed example; var/item, penalties default/4/0, increment1, bits5; nonmultiple example',
        full_instance='raw/rc, var/item, increment1/2; no sampling; never use default fine increment',
        seed_probe='10 repeated same-object and 10 fresh-seed toy SA calls',hardware_calls=0,new_fits=0),indent=2))
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'));from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def no_network(*a,**k):raise RuntimeError('Network prohibited for local probes')
    requests.sessions.Session.request=no_network
    a=np.array([[0.,-10,0,20,.55],[-10,0,6120,.5,60],[0,6120,0,0,-5120],[20,.5,0,0,1.025],[.55,60,-5120,1.025,0]])
    S=states(5);E=energy(S,a);rows=[]
    for it,h,d in [(0,'greedy','heuristic')]+[(100,h,d) for h in ['greedy','order'] for d in ['heuristic','random']]:
        name=f'mutate_{it}_{h}_{d}';row=dict(id=name)
        try:
            b=kw.preprocess.perform_precision_adaption_mutate(a.copy(),iterations=it,heuristic=h,decision=d)
            np.save(OUT/(name+'.npy'),b);F=energy(S,b);opt=F==F.min()
            row.update(maxJ=float(np.abs(b).max()),max_difference_from_twice_input=float(np.abs(b-2*a).max()),
                ground_subset_original=bool(np.all(E[opt]==E.min())),new_ground_count=int(sum(opt)))
        except Exception as e:row.update(error=type(e).__name__+': '+str(e)[:200])
        rows.append(row)
    base=np.array([[0.,18.,-12.],[18.,0.,1.],[-12.,1.,0.]])
    for method in ['item','var']:
        for pen in [None,4.,0.]:
            for fractional in [False,True]:
                a=base.copy()
                if fractional:a[1,2]=a[2,1]=1.3
                name=f'split_{method}_{pen}_{fractional}';row=dict(id=name)
                try:
                    b,idx=kw.preprocess.perform_precision_adaption_split(a.copy(),param_bit=5,min_increment=1.,penalty=pen,round_to_increment=True,method=method)
                    with (OUT/(name+'.npz')).open('xb') as f:np.savez_compressed(f,input=a,J=b,indices=idx)
                    assert len(b)<=20
                    X=states(len(b));Y=kw.preprocess.restore_split_solution(X,idx);F=energy(X,b);T=energy(Y,a)
                    original_min=energy(states(3),a).min();opt=F==F.min()
                    conditional=[]
                    for s in states(3):conditional.append(float(F[np.all(Y==s,axis=1)].min()+s@a@s))
                    row.update(spins=len(b),indices=np.asarray(idx).tolist(),maxJ=float(np.abs(b).max()),
                        integral=bool(np.allclose(b,np.rint(b))),ground_original_regret_max=float(T[opt].max()-original_min),
                        conditional_energy_offset_range=[min(conditional),max(conditional)],ground_count=int(sum(opt)))
                except Exception as e:row.update(error=type(e).__name__+': '+str(e)[:200])
                rows.append(row)
    # Explicit increments bound memory; do not call the default resolution on full input.
    for encoding in ['raw','rc']:
        path=ROOT/f'artifacts/p2_rescue1/representations/11-{encoding}-N8-rescue1.npz';a=np.load(path)['J']
        for method in ['item','var']:
            for delta in [1.,2.]:
                name=f'full_{encoding}_{method}_{delta}';row=dict(id=name,input_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                try:
                    t=time.monotonic();b,idx=kw.preprocess.perform_precision_adaption_split(a.copy(),param_bit=8,min_increment=delta,round_to_increment=True,method=method)
                    with (OUT/(name+'.npz')).open('xb') as f:np.savez_compressed(f,J=b,indices=idx,delta=delta)
                    row.update(spins=len(b),max_scaled_J=float(np.abs(b/delta).max()),integral=bool(np.allclose(b/delta,np.rint(b/delta))),
                        within550=len(b)<=550,seconds=time.monotonic()-t)
                except Exception as e:row.update(error=type(e).__name__+': '+str(e)[:200])
                rows.append(row)
    rng=np.random.default_rng(90210);a=rng.integers(-20,21,size=(30,30));a=np.triu(a,1);a=a+a.T
    args=dict(initial_temperature=100,cutoff_temperature=.1,alpha=.9,iterations_per_t=10,size_limit=1,process_num=1)
    solver=kw.classical.SimulatedAnnealingOptimizer(**args,rand_seed=1901)
    repeated=[np.asarray(solver.solve(a))[0].tolist() for _ in range(10)]
    fresh=[np.asarray(kw.classical.SimulatedAnnealingOptimizer(**args,rand_seed=1901+i).solve(a))[0].tolist() for i in range(10)]
    rows.append(dict(id='same_object_seed_probe',attempts=20,repeated_unique=len(set(map(tuple,repeated))),
        fresh_unique=len(set(map(tuple,fresh))),repeated=repeated,fresh=fresh))
    with (OUT/'results.json').open('x') as f:json.dump(rows,f,indent=2)
    for row in rows:print(json.dumps({k:v for k,v in row.items() if k not in ['repeated','fresh']}),flush=True)

if __name__=='__main__':main()
