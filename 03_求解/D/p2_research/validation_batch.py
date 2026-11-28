"""H07/H08: bounded, post-hoc registered validation; no fitting or CIM calls."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artifacts/p2_research_20261128/validation_H07_H08'

def build(q,order):
    groups=np.array_split(order,40);n=len(order)-40+1
    K=np.zeros((n,n),dtype=np.int64);meta=[];start=0
    for g in groups:
        m=len(g)-1;h=-np.diff(q[g]);h[0]+=64;h[-1]-=64
        ids=np.arange(start,start+m-1);K[ids,ids+1]=K[ids+1,ids]=64
        K[start:start+m,-1]=K[-1,start:start+m]=h
        meta.append(dict(start=start,stop=start+m,reference=n-1,mapping=g.tolist()))
        start+=m
    assert n<=550 and abs(K).max()<=127
    return K,meta

def save(name,K,q,v,meta,scale):
    p=OUT/name;p.mkdir()
    with (p/'matrix.npz').open('xb') as f:np.savez_compressed(f,J=K,q=q,values=v)
    (p/'blocks.json').write_text(json.dumps(meta))
    (p/'settings.json').write_text(json.dumps(dict(scale=scale)))

def prepare():
    OUT.mkdir(exist_ok=False)
    specs=[]
    # Exact reuse of H05, not rebuilding or reselection.
    for kind in ['real','zero']:
        p=ROOT/f'artifacts/p2_research_20261128/short_H05/40_{kind}'
        for b in range(5):
            name=f'blind_{kind}_{b:02d}';dest=OUT/name;dest.mkdir()
            for f in ['matrix.npz','blocks.json','settings.json']:(dest/f).symlink_to(p/f)
            specs.append(dict(name=name,seed=360001+100*b))
    z=np.load(ROOT/'artifacts/p23_v2/pool_11.npz');v=z['vhat'][:,:,0][z['allowed'][:,:,0]]
    r=v-v.min();R=r.max();q=np.rint(63*np.where(r<=2,.75*r/2,.75+.25*(r-2)/(R-2))).astype(np.int64)
    order=np.random.default_rng(863221).permutation(len(v))
    real,meta=build(q,order);zero=real.copy();zero[:,-1]=0;zero[-1,:]=0
    for b in meta:
        zero[b['start'],-1]=zero[-1,b['start']]=64
        zero[b['stop']-1,-1]=zero[-1,b['stop']-1]=-64
    for kind,K in [('real',real),('zero',zero)]:
        name=f'blind_permutation_{kind}';save(name,K,q,v,meta,float(4*abs(real).sum(1).max()));specs.append(dict(name=name,seed=361001))
    linear=np.rint(63*r/R).astype(np.int64);K,meta=build(linear,np.arange(len(v)))
    save('blind_linear',K,linear,v,meta,float(4*abs(K).sum(1).max()));specs.append(dict(name='blind_linear',seed=361101))
    z=np.load(ROOT/'artifacts/p23_v2/pool_07.npz');v=z['vhat'][:,:,0][z['allowed'][:,:,0]]
    r=v-v.min();R=r.max();q=np.rint(63*np.where(r<=2,.75*r/2,.75+.25*(r-2)/(R-2))).astype(np.int64)
    for b,order in enumerate(np.array_split(np.arange(len(v)),5)):
        real,meta=build(q,order);zero=real.copy();zero[:,-1]=0;zero[-1,:]=0
        for block in meta:
            zero[block['start'],-1]=zero[-1,block['start']]=64
            zero[block['stop']-1,-1]=zero[-1,block['stop']-1]=-64
        for kind,K in [('real',real),('zero',zero)]:
            name=f'full_batch{b}_{kind}';save(name,K,q,v,meta,float(4*abs(real).sum(1).max()));specs.append(dict(name=name,seed=362001+100*b))
    manifest={s['name']:hashlib.sha256((OUT/s['name']/'matrix.npz').read_bytes()).hexdigest() for s in specs}
    (OUT/'registration.json').write_text(json.dumps(dict(id='H07_H08',time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        context='Post-hoc exploratory validation after H05 and H04 complete; H05 40_real 99 feasible and72 optimal of100 observed.',
        objective='Replicate fixed H05; one cost-independent permutation and linear-map control; demonstrate complete2704 pool by5 disjoint batches.',
        specs=specs,restarts_each=100,total_restarts=len(specs)*100,groups=40,q_max=63,P=128,
        permutation_seed=863221,iterations_per_t=550,alpha=.99,cutoff_ratio=1e-4,temperature='4 max absolute real-matrix row sum; paired zero shares same temperature',
        decoder='Minimum(q,candidate row-major index) among unbroken prefix chains; strict all-chain feasibility separately. No repair.',
        full_pool_budget='Five separate matrices,100 samples each; merge candidate outcomes by common sample index. This is500 SA calls, not100. Zero control same budget.',
        scope='Not hardware preregistration, no significance/quantum speedup claim; zero control uses identical real-q classical selection.',
        stop='Run all23 predefined100-sample blocks, retain all failures. No new family or parameter sweep.',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),matrix_files_sha256=manifest),indent=2))
    print(json.dumps(dict(blocks=len(specs),samples=len(specs)*100)),flush=True)

def run(name,seed):
    p=OUT/name;z=np.load(p/'matrix.npz');K=z['J'];q=z['q'];v=z['values'];meta=json.loads((p/'blocks.json').read_text());scale=json.loads((p/'settings.json').read_text())['scale']
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'));from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def disabled(*a,**k):raise RuntimeError('Network prohibited after local license initialization')
    requests.sessions.Session.request=disabled
    start=time.monotonic();rows=[]
    with (p/'raw.jsonl').open('x') as f:
        for i in range(100):
            row=dict(index=i,seed=seed+i)
            try:
                opt=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=scale,cutoff_temperature=scale*1e-4,alpha=.99,iterations_per_t=550,rand_seed=seed+i,size_limit=1,process_num=1)
                a=np.asarray(opt.solve(K));assert a.shape==(1,len(K)) and np.isin(a,[-1,1]).all();s=a[0].astype(np.int64)
                valid=[];viol=[]
                for b in meta:
                    x=(s[b['start']:b['stop']]*s[-1]+1)//2;bad=int(sum(x[1:]>x[:-1]));viol.append(bad)
                    if not bad:valid.append(b['mapping'][int(sum(x))])
                chosen=min(valid,key=lambda c:(q[c],c)) if valid else None
                row.update(status='VALID_COMPLETED',spins=s.tolist(),energy=int(-s@K@s),valid_blocks=len(valid),block_violations=viol,
                    all_chains_feasible=len(valid)==len(meta),candidate=chosen,regret=float(v[chosen]-v.min()) if chosen is not None else None,
                    rank=int(1+sum(v<v[chosen])) if chosen is not None else None)
            except Exception as e:row.update(status='FAILED',error=type(e).__name__+': '+str(e)[:200])
            rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
    result=dict(name=name,attempts=100,valid=sum(r['status']=='VALID_COMPLETED' for r in rows),
        strict=sum(r.get('all_chains_feasible',False) for r in rows),hits=sum(r.get('regret')==0 for r in rows),seconds=time.monotonic()-start)
    (p/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)

def child(s):
    with (OUT/(s['name']+'.log')).open('x') as f:r=subprocess.run([sys.executable,__file__,'child',s['name'],str(s['seed'])],stdout=f,stderr=subprocess.STDOUT)
    return dict(name=s['name'],exit_code=r.returncode)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='child':run(sys.argv[2],int(sys.argv[3]))
    else:
        specs=json.loads((OUT/'registration.json').read_text())['specs']
        with ThreadPoolExecutor(4) as ex:result=list(ex.map(child,specs))
        (OUT/'process_outcomes.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
