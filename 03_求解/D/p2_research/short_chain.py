"""H05: unpadded short chains; fixed four-cell exploratory ablation."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np
from packed_checker import dp_chain, brute_check
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/p2_research_20261128/short_H05'
SETTINGS = [(g, kind) for g in [20, 40] for kind in ['real', 'zero']]

def prepare():
    OUT.mkdir(exist_ok=False)
    z = np.load(ROOT / 'artifacts/p23_v2/pool_11.npz')
    values = z['vhat'][:, :, 0][z['allowed'][:, :, 0]]
    regret = values - values.min(); R = regret.max()
    q = np.rint(63 * np.where(regret <= 2, .75 * regret / 2, .75 + .25 * (regret - 2) / (R - 2))).astype(np.int64)
    (OUT / 'registration.json').write_text(json.dumps(dict(id='H05', time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        context='Exploratory after H02/H03; H04 first two blocks observed; no hardware selection.',
        hypothesis='Shorter chains without duplicate endpoints may improve strict feasibility; 63 levels and P128 bound all edge coefficients by127.',
        groups=[20,40],settings=['real','zero'],source_order='row-major permitted candidates, no cost sorting',
        seeds='340001..340100 paired four cells',restarts=100,iterations_per_t=550,alpha=.99,cutoff_ratio=1e-4,
        temperature='4 max absolute row sum of real matrix, shared with its zero control',
        decoder='valid chain extraction; smallest original q then row-major index; strict all-chain outcome separately',
        stop='All four fixed cells; no early stop or parameter adjustment; no hardware calls or model fits.',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2))
    certs={}
    for groups in [20,40]:
        n=len(q)-groups+1;J=np.zeros((n,n),dtype=np.int64);meta=[];start=0
        for block in np.array_split(np.arange(len(q)),groups):
            size=len(block)-1;h=-np.diff(q[block]);h[0]+=64;h[-1]-=64
            ids=np.arange(start,start+size-1);J[ids,ids+1]=J[ids+1,ids]=64
            J[start:start+size,-1]=J[-1,start:start+size]=h
            meta.append(dict(start=start,stop=start+size,reference=n-1,mapping=block.tolist()))
            start+=size
        assert start==n-1
        zero=J.copy();zero[:-1,-1]=zero[-1,:-1]=0
        for b in meta:
            zero[b['start'],-1]=zero[-1,b['start']]=64
            zero[b['stop']-1,-1]=zero[-1,b['stop']-1]=-64
        scale=float(4*np.abs(J).sum(1).max())
        for kind,K in [('real',J),('zero',zero)]:
            name=f'{groups}_{kind}';folder=OUT/name;folder.mkdir()
            assert len(K)<=550 and np.abs(K).max()<=127
            gaps=[];legalmin=0
            for b in meta:
                ids=list(range(b['start'],b['stop']))+[n-1];part=K[np.ix_(ids,ids)];good,bad=dp_chain(part)
                energies=[]
                for t in range(len(ids)):
                    s=np.r_[np.ones(t,dtype=int),-np.ones(len(ids)-1-t,dtype=int),1]
                    energies.append(int(-s@part@s))
                costs=q[b['mapping']] if kind=='real' else np.zeros(len(ids))
                assert np.unique(np.array(energies)-4*costs).size==1 and good==min(energies) and bad>good
                gaps.append(bad-good);legalmin+=good
            with (folder/'matrix.npz').open('xb') as f:np.savez_compressed(f,J=K,q=q,values=values)
            (folder/'blocks.json').write_text(json.dumps(meta))
            (folder/'settings.json').write_text(json.dumps(dict(scale=scale)))
            certs[name]=dict(status='CERTIFIED',spins=n,max_J=int(abs(K).max()),illegal_gap=min(gaps),ground_energy=legalmin,
                G2_original_worst_regret=float(regret[q==0].max()) if kind=='real' else float(R),
                note='Zero is certified for chain feasibility only, deliberately does not preserve business optimum.')
    (OUT/'certificates.json').write_text(json.dumps(dict(tiny_independent_states=brute_check(),matrices=certs),indent=2))
    print(json.dumps(certs),flush=True)

def run(name):
    f=OUT/name;z=np.load(f/'matrix.npz');K=z['J'];q=z['q'];v=z['values'];r=v-v.min()
    meta=json.loads((f/'blocks.json').read_text());scale=json.loads((f/'settings.json').read_text())['scale']
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'));from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def no_network(*a,**k):raise RuntimeError('Network prohibited during local SA')
    requests.sessions.Session.request=no_network
    rows=[];start=time.monotonic()
    with (f/'raw.jsonl').open('x') as stream:
        for i in range(100):
            row=dict(index=i,seed=340001+i)
            try:
                solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=scale,cutoff_temperature=scale*1e-4,alpha=.99,
                    iterations_per_t=550,rand_seed=340001+i,size_limit=1,process_num=1)
                a=np.asarray(solver.solve(K));assert a.shape==(1,len(K)) and np.isin(a,[-1,1]).all()
                s=a[0].astype(np.int64);c=[];viol=[]
                for b in meta:
                    x=(s[b['start']:b['stop']]*s[-1]+1)//2;bad=int(sum(x[1:]>x[:-1]));viol.append(bad)
                    if not bad:c.append(b['mapping'][int(x.sum())])
                chosen=min(c,key=lambda t:(q[t],t)) if c else None
                row.update(status='VALID_COMPLETED',spins=s.tolist(),energy=int(-s@K@s),valid_blocks=len(c),block_violations=viol,
                    all_chains_feasible=len(c)==len(meta),candidate=chosen,regret=float(r[chosen]) if chosen is not None else None,
                    rank=int(1+sum(v<v[chosen])) if chosen is not None else None)
            except Exception as e:row.update(status='FAILED',error=type(e).__name__+': '+str(e)[:200])
            rows.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
    good=[r for r in rows if r.get('candidate') is not None]
    summary=dict(setting=name,attempted=100,valid=sum(r['status']=='VALID_COMPLETED' for r in rows),
        strict_feasible=sum(r.get('all_chains_feasible',False) for r in rows),usable=len(good),hits=sum(r['regret']==0 for r in good),
        strict_hits=sum(r['regret']==0 and r['all_chains_feasible'] for r in good),near2=sum(r['regret']<=2 for r in good),
        top20=sum(r['rank']<=20 for r in good),median_rank=float(np.median([r['rank'] for r in good])) if good else None,
        seconds=time.monotonic()-start)
    (f/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

def child(spec):
    name=f'{spec[0]}_{spec[1]}'
    with (OUT/f'{name}.log').open('x') as f:
        p=subprocess.run([sys.executable,__file__,name],stdout=f,stderr=subprocess.STDOUT)
    return dict(setting=name,exit_code=p.returncode)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run_all':
        with ThreadPoolExecutor(4) as ex:result=list(ex.map(child,SETTINGS))
        (OUT/'process_outcomes.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
    else:run(sys.argv[1])
