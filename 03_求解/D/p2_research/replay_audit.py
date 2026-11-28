"""Independent saved-state replay; no solver, license, fitter or builder imports."""
from pathlib import Path
import hashlib, json, math, sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artifacts/p2_research_20261128'

def read_rows(file):
    return [json.loads(line) for line in file.read_text().splitlines()]

def replay(J,q,v,blocks,rows):
    assert J.dtype.kind in 'iu' and np.array_equal(J,J.T) and np.abs(J).max()<=127 and not np.diag(J).any()
    assert len({r['seed'] for r in rows})==len(rows)
    counters=dict(attempts=len(rows),valid=0,strict_feasible=0,usable=0,hits=0,strict_hits=0,near2=0,top20=0,total_valid_subproblems=0)
    ranks=[];regrets=[];strict_regrets=[]
    for row in rows:
        if row['status']!='VALID_COMPLETED':continue
        s=np.array(row['spins'],dtype=np.int64)
        assert s.shape==(len(J),) and np.isin(s,[-1,1]).all() and int(-s@J@s)==row['energy']
        counters['valid']+=1;valid=[];viol=[]
        for b in blocks:
            ref=b.get('reference',len(J)-1)
            spins=s[b['start']:b['stop']]*s[ref]
            transitions=sum(spins[:-1]<spins[1:]);viol.append(int(transitions))
            if transitions==0:
                valid.append(b['mapping'][int(np.sum(spins==1))])
        full=len(valid)==len(blocks)
        assert len(valid)==row['valid_blocks'] and full==row['all_chains_feasible'] and viol==row['block_violations']
        selected=min(valid,key=lambda c:(q[c],c)) if valid else None
        assert selected==row['candidate']
        counters['strict_feasible']+=full;counters['total_valid_subproblems']+=len(valid)
        if selected is None:
            assert row['regret'] is None and row['rank'] is None
            continue
        regret=float(v[selected]-v.min());rank=int(1+np.count_nonzero(v<v[selected]))
        assert regret==row['regret'] and rank==row['rank']
        counters['usable']+=1;counters['hits']+=regret==0;counters['strict_hits']+=full and regret==0
        counters['near2']+=regret<=2;counters['top20']+=rank<=20
        ranks.append(rank);regrets.append(regret)
        if full:strict_regrets.append(regret)
    counters['conditional_median_rank']=float(np.median(ranks)) if ranks else None
    counters['conditional_regret_quantiles']=np.quantile(regrets,[0,.5,.9,.95,1]).tolist() if regrets else None
    counters['strict_conditional_regret_quantiles']=np.quantile(strict_regrets,[0,.5,.9,.95,1]).tolist() if strict_regrets else None
    for key in ['hits','strict_hits']:
        p=counters[key]/len(rows)
        counters[key+'_ps']=p
        counters[key+'_R99_plugin']=math.ceil(math.log(.01)/math.log1p(-p)) if 0<p<1 else (1 if p==1 else None)
    counters['R99_note']='Descriptive plug-in number of independent same-distribution SA restarts; zero hits gives undefined/infinite estimate, not proof p=0. Not CIM TTS; concurrent wall time not used.'
    return counters

def basic_chains():
    report={}
    for root in ['shaping_H03','short_H05']:
        for folder in sorted((OUT/root).iterdir()):
            if not folder.is_dir() or not (folder/'raw.jsonl').exists():continue
            rows=read_rows(folder/'raw.jsonl');assert len(rows)==100
            z=np.load(folder/'matrix.npz');blocks=json.loads((folder/'blocks.json').read_text())
            report[str(folder.relative_to(OUT))]=replay(z['J'],z['q'],z['values'],blocks,rows)
    return report

def negative():
    p=OUT/'negative_H04';z=np.load(p/'matrices.npz');blocks=json.loads((p/'blocks.json').read_text());report={}
    for kind in ['real','zero']:
        allrows=[];separate=[]
        for block in range(5):
            folder=p/f'{kind}_{block:02d}'
            if not (folder/'raw.jsonl').exists():folder=p/'initialization_recovery'/folder.name
            rows=read_rows(folder/'raw.jsonl');assert len(rows)==100;allrows+=rows
            r=replay(z[kind],z['q'],z['values'],blocks,rows);r['block']=block
            available=[a for a in rows if a.get('candidate') is not None]
            best=min(available,key=lambda a:(z['q'][a['candidate']],a['candidate'],a['index'])) if available else None
            r['best_regret']=best['regret'] if best else None
            separate.append(r)
        report[kind]=dict(pooled=replay(z[kind],z['q'],z['values'],blocks,allrows),blocks=separate)
    report['recovery']='Six pre-SA initialization failures retained; 400 original and 600 recovered first-run samples. No completed sample rerun.'
    return report

def raw_models():
    pool=np.load(ROOT/'artifacts/p23_v2/pool_11.npz');mask=pool['allowed'][:,:,0];v=pool['vhat'][:,:,0];report={}
    for name in ['split_SA_B01','oracle_G02']:
        if name=='split_SA_B01':
            z=np.load(OUT/'split_resolution/float_raw_var_0.25.npz');J=np.rint(z['J']/z['delta']).astype(np.int64);idx=z['indices'];starts=np.r_[0,idx[:-1]+1]
        else:
            z=np.load(OUT/name/'matrix.npz');J=z['J'];idx=np.arange(len(J));starts=idx
        rows=read_rows(OUT/name/'raw.jsonl');assert len(rows)==100
        counts=dict(attempts=100,valid=0,copy_consistent=0,feasible=0,hits=0)
        for r in rows:
            if r['status']!='VALID_COMPLETED':continue
            s=np.array(r['spins'],dtype=np.int64);assert s.shape==(len(J),) and np.isin(s,[-1,1]).all()
            assert int(-s@J@s)==r['energy'];counts['valid']+=1
            coherent=all(np.all(s[lo:hi+1]==s[hi]) for lo,hi in zip(starts,idx));counts['copy_consistent']+=coherent
            spins=s[idx]*s[idx[-1]];aa=np.flatnonzero(spins[:52]==1);bb=np.flatnonzero(spins[52:104]==1)
            feas=coherent and len(aa)==len(bb)==1 and bool(mask[aa[0],bb[0]])
            assert feas==r['feasible'];counts['feasible']+=feas
            if feas:
                regret=float(v[aa[0],bb[0]]-v[mask].min());assert regret==r['regret'];counts['hits']+=regret==0
        report[name]=counts
    return report

if __name__=='__main__':
    mode=sys.argv[1]
    result=negative() if mode=='negative' else basic_chains() if mode=='chains' else raw_models()
    dest=OUT/f'independent_replay_{mode}.json'
    with dest.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
