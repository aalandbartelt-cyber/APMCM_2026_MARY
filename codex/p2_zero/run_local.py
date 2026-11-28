"""Run preregistered CPU-only paired SA. Raw outcomes are exclusive, never replaced."""
import csv, hashlib, json, os, signal, sys, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/'codex/p2_zero'
RUN=ROOT/'artifacts/p2_zero'
SRC=ROOT/'artifacts/p2_research_20261128/short_H05'
def folder(arm):
    return RUN/'single_real' if arm=='single_real' else SRC/arm
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
    from validation_checker import certify
    z=np.load(SRC/'40_real/matrix.npz'); q=z['q']; n=len(q)
    K=np.zeros((n,n),dtype=np.int64)
    idx=np.arange(n-2); K[idx,idx+1]=K[idx+1,idx]=64
    h=-np.diff(q);h[0]+=64;h[-1]-=64;K[-1,:-1]=K[:-1,-1]=h
    p=folder('single_real');p.mkdir()
    np.savez_compressed(p/'matrix.npz',J=K,q=q,values=z['values'])
    (p/'blocks.json').write_text(json.dumps([dict(start=0,stop=n-1,reference=n-1,mapping=list(range(n)))]))
    cert=certify(p)
    assert cert['G1']==cert['G2']=='CERTIFIED' and cert['batch_ground_worst_regret']==0
    (REG/'single_certificate.json').write_text(json.dumps(cert,indent=2))
    tasks=[(arm,b) for b in range(20) for arm in (('40_real','40_zero','single_real') if b<2 else ('40_real','40_zero'))]
    seeds=set(range(710001,712001))
    import re
    pat=re.compile(rb'"(?:rand_seed|seed)"\s*:\s*(\d+)')
    checked=0
    for p in (ROOT/'artifacts').rglob('*.jsonl'):
        if RUN in p.parents:continue
        with p.open('rb') as f:
            for line in f:
                for m in pat.finditer(line):
                    checked+=1
                    assert int(m.group(1)) not in seeds, str(p)
    with (REG/'slots.csv').open('x') as f:
        w=csv.writer(f);w.writerow(['arm','block','index','seed'])
        for arm,b in tasks:
            for i in range(100):w.writerow([arm,b,i,710001+100*b+i])
    paths=[Path(__file__),REG/'slots.csv',REG/'validation_checker.py',REG/'single_certificate.json']
    for arm in ('40_real','40_zero','single_real'):
        paths += [folder(arm)/x for x in ('matrix.npz','blocks.json')]
    spec=dict(tasks=tasks,cutoff='2026-11-28T20:13:45+08:00',charged_plan_minutes=30,init_temperature=26284,alpha=.99,cutoff_ratio=.0001,iterations_per_t=550,process_num=1,size_limit=1,
              prior_seed_fields_checked=checked,budgets=[1,2,5,10,20,50,100],main='B=5 two-sided exact McNemar, alpha=.05, 20 fresh seed-block pairs; incomplete block suppresses test; failed attempts count as misses. Primary: any strict regret=0; secondary: strict min(E,index). No replacement.',
              hashes={str(p.relative_to(ROOT)):sha(p) for p in paths})
    (REG/'registration.json').write_text(json.dumps(spec,indent=2))
def init_worker():
    import fcntl, kaiwu as kw, requests
    sys.path.insert(0,str(ROOT/'configs'))
    from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    with (RUN/'license.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    def offline(*args,**kwargs): raise RuntimeError('Network disabled for local SA')
    requests.sessions.Session.request=offline
def run(task):
    from datetime import datetime
    import kaiwu as kw
    arm,b=task;p=folder(arm);z=np.load(p/'matrix.npz');K=z['J'];v=z['values'];q=z['q']
    blocks=json.loads((p/'blocks.json').read_text());cut=datetime.fromisoformat(json.loads((REG/'registration.json').read_text())['cutoff']).timestamp()
    with (RUN/f'{arm}_{b:02}.jsonl').open('x',buffering=1) as f:
        for i in range(100):
            if time.time()>=cut:break
            seed=710001+100*b+i
            row=dict(index=i,seed=seed)
            try:
                opt=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=26284.,cutoff_temperature=2.6284,alpha=.99,iterations_per_t=550,rand_seed=seed,size_limit=1,process_num=1)
                a=np.asarray(opt.solve(K));assert a.shape==(1,len(K)) and np.isin(a,[-1,1]).all()
                s=a[0].astype(np.int64);choices=[]
                for g in blocks:
                    d=s[g['start']:g['stop']]*s[-1]
                    if np.all(d[1:]<=d[:-1]):choices.append(g['mapping'][int(sum(d==1))])
                c=min(choices,key=lambda c:(q[c],c)) if choices else None
                row.update(status='VALID_COMPLETED',bits=np.packbits(s>0).tobytes().hex(),energy=int(-s@K@s),all_chains_feasible=len(choices)==len(blocks),candidate=c,regret=float(v[c]-v.min()) if c is not None else None,valid_blocks=len(choices))
            except Exception as err:
                row.update(status='FAILED',error=type(err).__name__)
            f.write(json.dumps(row)+'\n')
    return arm,b
if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':
        spec=json.loads((REG/'registration.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in spec['hashes'].items())
        with (RUN/'run_intent').open('x') as f:f.write(str(time.time()))
        with ProcessPoolExecutor(4,initializer=init_worker) as ex:
            for task in ex.map(run,spec['tasks']):print('completed',*task,flush=True)
