"""H03: cost-independent decomposition with shared vs independent reference spins."""
from pathlib import Path
import os,sys,json,hashlib,datetime,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from shaping_experiment import make_q,construct
from packed_checker import dp_chain
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/p2_research_20261128/shaping_H03'
SETTINGS={'shared10':('shared',550,'shared'),'independent10':('independent',550,'own'),
          'independent10_sharedT':('independent',550,'shared'),'independent10_short':('independent',10,'own')}

def prepare():
    OUT.mkdir(exist_ok=False);src=ROOT/'artifacts/p23_v2/pool_11.npz';z=np.load(src)
    v=z['vhat'][:,:,0][z['allowed'][:,:,0]];q=make_q(v-v.min(),'piecewise2')
    common,blocks=construct(q,10,P=254);common_scale=4*np.abs(common).sum(1).max()
    reg=dict(id='H03',time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        hypothesis='Shared reference high row norm may affect finite-budget dynamics; factor temperature separately.',
        context='Exploratory followup after H02, all settings fixed before sampling',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
        settings=SETTINGS,groups=10,P=254,family='piecewise2',seeds='300001..300100 common across all four',
        restarts=100,alpha=.99,cutoff_ratio=.0001,size_limit=1,no_repair=True,hardware_calls=0,new_fits=0)
    certs={}
    for name,(mode,iterations,temperature) in SETTINGS.items():
        f=OUT/name;f.mkdir()
        if mode=='shared':
            J=common.copy();meta=[dict(b,reference=len(J)-1) for b in blocks]
        else:
            n=sum(b['stop']-b['start']+1 for b in blocks);J=np.zeros((n,n),dtype=np.int64);meta=[];start=0
            for b in blocks:
                ids=list(range(b['start'],b['stop']))+[len(common)-1];part=common[np.ix_(ids,ids)];end=start+len(part)
                J[start:end,start:end]=part
                meta.append(dict(start=start,stop=end-1,reference=end-1,mapping=b['mapping'],q=b['q']));start=end
        assert len(J)<=550 and np.abs(J).max()<=127
        # Independent DP uses only the exported submatrix; verify the cost embedding too.
        cover=set();totalgood=0;gaps=[];allowed=np.zeros_like(J,dtype=bool)
        for b in meta:
            ids=list(range(b['start'],b['stop']))+[b['reference']];K=J[np.ix_(ids,ids)];good,bad=dp_chain(K)
            energies=[]
            for t in range(len(ids)):
                s=np.r_[np.ones(t,dtype=int),-np.ones(len(ids)-1-t,dtype=int),1]
                energies.append(int(-s@K@s))
            assert np.unique(np.array(energies)-4*q[b['mapping']]).size==1
            assert good==min(energies) and bad>good
            totalgood+=good;gaps.append(bad-good);cover.update(ids);allowed[np.ix_(ids,ids)]=True
        assert cover==set(range(len(J))) and not J[~allowed].any()
        certs[name]=dict(status='CERTIFIED',spins=len(J),illegal_gap=min(gaps),ground_energy=totalgood,
            worst_original_ground_regret=float((v-v.min())[q==q.min()].max()))
        with (f/'matrix.npz').open('xb') as h:np.savez_compressed(h,J=J,q=q,values=v)
        (f/'blocks.json').write_text(json.dumps(meta))
        scale=float(common_scale if temperature=='shared' else 4*np.abs(J).sum(1).max())
        (f/'settings.json').write_text(json.dumps(dict(iterations_per_t=iterations,scale=scale)))
    (OUT/'registration.json').write_text(json.dumps(reg,indent=2));(OUT/'certificates.json').write_text(json.dumps(certs,indent=2))
    print(json.dumps(certs),flush=True)

def run(name):
    assert name in SETTINGS;f=OUT/name;z=np.load(f/'matrix.npz');J=z['J'];q=z['q'];v=z['values'];r=v-v.min()
    blocks=json.loads((f/'blocks.json').read_text());settings=json.loads((f/'settings.json').read_text());scale=settings['scale']
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'));from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def no_network(*a,**k):raise RuntimeError('Network prohibited during local SA')
    requests.sessions.Session.request=no_network
    rows=[];start=time.monotonic()
    with (f/'raw.jsonl').open('x') as stream:
        for i in range(100):
            row=dict(index=i,seed=300001+i)
            try:
                solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=scale,cutoff_temperature=scale*1e-4,
                    alpha=.99,iterations_per_t=settings['iterations_per_t'],size_limit=1,rand_seed=300001+i,process_num=1)
                a=np.asarray(solver.solve(J));assert a.shape==(1,len(J)) and np.isin(a,[-1,1]).all()
                s=a[0].astype(np.int64);c=[];viol=[]
                for b in blocks:
                    x=(s[b['start']:b['stop']]*s[b['reference']]+1)//2;bad=int(sum(x[1:]>x[:-1]));viol.append(bad)
                    if not bad:c.append(b['mapping'][int(x.sum())])
                chosen=min(c,key=lambda t:(q[t],t)) if c else None
                row.update(status='VALID_COMPLETED',spins=s.tolist(),energy=int(-s@J@s),valid_blocks=len(c),
                    all_chains_feasible=len(c)==len(blocks),block_violations=viol,candidate=chosen,
                    regret=float(r[chosen]) if chosen is not None else None,rank=int(1+sum(v<v[chosen])) if chosen is not None else None)
            except Exception as e:row.update(status='FAILED',error_type=type(e).__name__,error=str(e)[:200])
            stream.write(json.dumps(row)+'\n');stream.flush();rows.append(row)
            if (i+1)%25==0:print(name,i+1,round(time.monotonic()-start,2),flush=True)
    good=[r for r in rows if r.get('candidate') is not None]
    summary=dict(setting=name,attempted=100,valid=sum(r['status']=='VALID_COMPLETED' for r in rows),
        all_chains_feasible=sum(r.get('all_chains_feasible',False) for r in rows),usable=len(good),
        valid_blocks=sum(r.get('valid_blocks',0) for r in rows),ps=sum(r['regret']==0 for r in good)/100,
        strict_ps=sum(r['regret']==0 and r['all_chains_feasible'] for r in good)/100,
        near2_rate=sum(r['regret']<=2 for r in good)/100,top20_rate=sum(r['rank']<=20 for r in good)/100,
        median_rank=float(np.median([r['rank'] for r in good])) if good else None,
        regret_quantiles=np.quantile([r['regret'] for r in good],[0,.5,.9,1]).tolist() if good else None,
        seconds=time.monotonic()-start)
    (f/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    else:run(sys.argv[1])
