"""F02/H06: exact int8 two-level cost coarsening, including mask-only control.

Known full-table minimum is used to define tolerance sets. This is screening-
conditioned sampling, not autonomous discovery of those sets or a speedup.
"""
from pathlib import Path
import datetime, hashlib, itertools, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/p2_research_20261128/threshold_F02'
SETTINGS=['eps01','eps2','mask_only']

def matrix(cost):
    m,n=cost.shape;N=m+n;Q=np.zeros((N,N),dtype=float)
    np.fill_diagonal(Q,-.5)
    for ids in [range(m),range(m,N)]:
        for i,j in itertools.combinations(ids,2):Q[i,j]=1
    Q[:m,m:]=cost
    # 8 times the SDK symmetric J: E_K = 8 x^T Q x + constant.
    K=np.zeros((N+1,N+1),dtype=np.int64);K[:N,:N]=-np.rint(Q+Q.T).astype(np.int64);np.fill_diagonal(K,0)
    K[:N,N]=K[N,:N]=-np.rint(Q.sum(1)+Q.sum(0)).astype(np.int64)
    return K

def prepare():
    OUT.mkdir(exist_ok=False)
    (OUT/'registration.json').write_text(json.dumps(dict(id='F02_H06',time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        context='Post-hoc exploratory construction after prior failure and H01-H05 design; no hardware authorization.',
        cost='q=0 on allowed regret<=epsilon, 1 otherwise; mask_only q=0 on all allowed. Equivalent nearest quantization of strictly increasing r/(r+epsilon), with threshold ties assigned0.',
        epsilons=[.1,2],penalty=.5,scale=8,seeds='350001..350100 paired across three settings',
        iterations_per_t=550,initial_temperature='4 max absolute row sum per matrix',alpha=.99,cutoff_ratio=1e-4,
        decoder='one A and one B AND allowed; raw, no repair, one candidate per sample',
        caveat='Full-table minimum and tolerance membership computed classically; within-zero-layer ranking intentionally discarded. Not autonomous discovery of target set.',
        stop='Three fixed cells x100; no followup parameter search in this experiment.',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),hardware_calls=0,new_fits=0),indent=2))
    pool=np.load(ROOT/'artifacts/p23_v2/pool_11.npz');mask=pool['allowed'][:,:,0];v=pool['vhat'][:,:,0];r=v-v[mask].min()
    certs={}
    for name in SETTINGS:
        threshold={'eps01':.1,'eps2':2,'mask_only':float('inf')}[name]
        targets=mask&(r<=threshold);cost=np.where(targets,0,1).astype(np.int64);K=matrix(cost)
        assert K.shape==(105,105) and abs(K).max()<=127 and targets.any()
        # Independent reconstruction through full spin energy for every one-hot state.
        offsets=[];groundregrets=[]
        for a in range(52):
            for b in range(52):
                s=-np.ones(105,dtype=np.int64);s[a]=s[52+b]=s[-1]=1
                offsets.append(int(-s@K@s)-8*int(cost[a,b]))
                if cost[a,b]==0:
                    assert mask[a,b];groundregrets.append(float(r[a,b]))
        assert len(set(offsets))==1
        folder=OUT/name;folder.mkdir()
        with (folder/'matrix.npz').open('xb') as f:np.savez_compressed(f,J=K,cost=cost,targets=targets)
        certs[name]=dict(status='CERTIFIED',spins=105,max_J=int(abs(K).max()),target_count=int(targets.sum()),
            G1='H=sum(q_ab*x_a*y_b)+.5[(sumx-1)^2+(sumy-1)^2]; q>=0, allowed zero-cost state exists. Every wrong-cardinality state H>=.5, forbidden one-hot H=1, minimum H=0.',
            physical_illegal_gap_lower_bound=4,onehot_states_checked=2704,ground_worst_original_regret=max(groundregrets),
            G2_eps01=max(groundregrets)<=.1,certificate_scope='Integer matrix ground-state representation; not sampling or true material validity.',
            ground_energy=offsets[0])
    # Test complete energy identity on small nonrectangular masked instance.
    C=np.array([[1,0,1],[1,1,0]]);K=matrix(C);off=[]
    for bits in itertools.product([0,1],repeat=5):
        x=np.array(bits[:2]);y=np.array(bits[2:]);s=np.r_[2*np.array(bits)-1,1]
        H=float(x@C@y+.5*((x.sum()-1)**2+(y.sum()-1)**2));off.append(int(-s@K@s)-8*H)
    assert len(set(off))==1
    (OUT/'certificates.json').write_text(json.dumps(dict(tiny_fullspace_states=32,matrices=certs),indent=2));print(json.dumps(certs),flush=True)

def run(name):
    f=OUT/name;K=np.load(f/'matrix.npz')['J'];pool=np.load(ROOT/'artifacts/p23_v2/pool_11.npz')
    mask=pool['allowed'][:,:,0];v=pool['vhat'][:,:,0];scale=float(4*abs(K).sum(1).max())
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'));from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def no_network(*a,**k):raise RuntimeError('Network prohibited during local SA')
    requests.sessions.Session.request=no_network
    rows=[];start=time.monotonic()
    with (f/'raw.jsonl').open('x') as stream:
        for i in range(100):
            row=dict(index=i,seed=350001+i)
            try:
                solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=scale,cutoff_temperature=scale*1e-4,
                    alpha=.99,iterations_per_t=550,rand_seed=350001+i,size_limit=1,process_num=1)
                a=np.asarray(solver.solve(K));assert a.shape==(1,105) and np.isin(a,[-1,1]).all()
                s=a[0].astype(np.int64);t=s*s[-1];aa=np.flatnonzero(t[:52]==1);bb=np.flatnonzero(t[52:104]==1)
                feas=len(aa)==len(bb)==1 and bool(mask[aa[0],bb[0]])
                row.update(status='VALID_COMPLETED',spins=s.tolist(),energy=int(-s@K@s),feasible=bool(feas),
                    regret=float(v[aa[0],bb[0]]-v[mask].min()) if feas else None,
                    rank=int(1+sum(v[mask]<v[aa[0],bb[0]])) if feas else None)
            except Exception as e:row.update(status='FAILED',error=type(e).__name__+': '+str(e)[:200])
            stream.write(json.dumps(row)+'\n');stream.flush();rows.append(row)
    good=[r for r in rows if r.get('feasible',False)]
    report=dict(setting=name,attempted=100,valid=sum(r['status']=='VALID_COMPLETED' for r in rows),feasible=len(good),
        hits=sum(r['regret']==0 for r in good),near2=sum(r['regret']<=2 for r in good),top20=sum(r['rank']<=20 for r in good),
        conditional_median_rank=float(np.median([r['rank'] for r in good])) if good else None,
        conditional_regret_quantiles=np.quantile([r['regret'] for r in good],[0,.5,.9,1]).tolist() if good else None,seconds=time.monotonic()-start)
    (f/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

def child(name):
    with (OUT/f'{name}.log').open('x') as f:r=subprocess.run([sys.executable,__file__,name],stdout=f,stderr=subprocess.STDOUT)
    return dict(setting=name,exit_code=r.returncode)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run_all':
        with ThreadPoolExecutor(3) as ex:result=list(ex.map(child,SETTINGS))
        (OUT/'process_outcomes.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
    else:run(sys.argv[1])
