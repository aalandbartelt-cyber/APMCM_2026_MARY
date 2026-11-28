"""Matrix-only independent DP and replay for disconnected chains sharing a reference.

No imports from matrix construction or sampling modules. Energy convention -s^T J s.
"""
from pathlib import Path
import json, itertools, hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3]

def dp_chain(K):
    n=len(K)-1
    dp={(s,False):-2*int(K[0,n])*s for s in [-1,1]}
    for i in range(1,n):
        nxt={}
        for (p,b),e in dp.items():
            for s in [-1,1]:
                key=(s,b or (p==-1 and s==1))
                cost=e-2*int(K[i,n])*s-2*int(K[i-1,i])*p*s
                nxt[key]=min(nxt.get(key,float('inf')),cost)
        dp=nxt
    return [min(e for (s,b),e in dp.items() if b==flag) for flag in [False,True]]

def brute_check():
    rng=np.random.default_rng(721119);count=0
    for n in range(2,10):
        for _ in range(10):
            K=np.zeros((n+1,n+1),dtype=np.int64)
            for i in range(n-1):K[i,i+1]=K[i+1,i]=rng.integers(-20,21)
            K[:n,n]=K[n,:n]=rng.integers(-20,21,size=n)
            vals=[[],[]]
            for path in itertools.product([-1,1],repeat=n):
                s=np.array((*path,1));bad=any(path[i]<path[i+1] for i in range(n-1))
                vals[int(bad)].append(int(-s@K@s));count+=1
            assert dp_chain(K)==[min(v) for v in vals]
    return count

def check(folder):
    z=np.load(folder/'matrix.npz');K=z['J'];q=z['q'];values=z['values']
    blocks=json.loads((folder/'blocks.json').read_text());n=len(K)-1
    assert K.dtype.kind in 'iu' and np.array_equal(K,K.T)
    assert np.abs(K).max()<=127 and not np.diag(K).any() and len(K)<=550
    coverage=[];business=[];allowed_edges=np.zeros_like(K,dtype=bool);stats=[]
    for b in blocks:
        ids=list(range(b['start'],b['stop']));coverage+=ids;business+=b['mapping'][1:-1]
        for a,c in zip(ids[:-1],ids[1:]):allowed_edges[a,c]=allowed_edges[c,a]=True
        allowed_edges[ids,n]=allowed_edges[n,ids]=True
        sub=K[np.ix_(ids+[n],ids+[n])];good,bad=dp_chain(sub);energies=[]
        for t in range(len(ids)+1):
            s=np.r_[np.ones(t,dtype=np.int64),-np.ones(len(ids)-t,dtype=np.int64),1]
            energies.append(int(-s@sub@s))
        energies=np.array(energies);mapped=q[b['mapping']]
        assert np.unique(energies-4*mapped).size==1 and energies.min()==good
        assert np.array_equal(mapped,np.array(b['q']))
        stats.append(dict(good=good,bad=bad,gap=bad-good,legal_states=len(energies)))
    assert coverage==list(range(n)) and business==list(range(len(values)))
    assert not K[~allowed_edges].any()
    result=dict(status='CERTIFIED' if min(x['gap'] for x in stats)>0 else 'COUNTEREXAMPLE',
        integer_spins=len(K),max_J=int(np.abs(K).max()),blocks=len(blocks),
        states=f'2^{n} reference-fixed states',global_legal_min=sum(x['good'] for x in stats),
        illegal_gap=min(x['gap'] for x in stats),
        original_ground_worst_regret=float(values[q==q.min()].max()-values.min()),
        original_candidates=len(values),matrix_sha256=hashlib.sha256((folder/'matrix.npz').read_bytes()).hexdigest(),
        per_block=stats)
    if (folder/'raw.jsonl').exists():
        rows=[json.loads(x) for x in (folder/'raw.jsonl').read_text().splitlines()];valid=0;full=0;usable=0
        random_uniform_top20=0.;random_stratified_top20=0.;random_stratified_ps=0.
        for r in rows:
            if r['status']!='VALID_COMPLETED':continue
            s=np.array(r['spins'],dtype=np.int64);assert len(s)==len(K) and np.isin(s,[-1,1]).all()
            assert int(-s@K@s)==r['energy'];valid+=1;g=s[:-1]*s[-1];candidates=[];miss20=1.;miss0=1.
            for b in blocks:
                a=g[b['start']:b['stop']];bad=int(sum(a[1:]>a[:-1]))
                if not bad:
                    candidates.append(b['mapping'][int(sum(a==1))])
                    group=np.unique(b['mapping']);v=values[group]
                    miss20*=1-float(np.mean([1+sum(values<t)<=20 for t in v]))
                    miss0*=1-float(np.mean(v==values.min()))
            assert len(candidates)==r['valid_blocks']
            full+=len(candidates)==len(blocks);usable+=bool(candidates)
            chosen=min(candidates,key=lambda c:(q[c],c)) if candidates else None
            assert chosen==r['candidate']
            if chosen is not None:
                assert r['regret']==float(values[chosen]-values.min()) and r['rank']==int(1+sum(values<values[chosen]))
            random_uniform_top20+=1-(1-20/len(values))**len(candidates)
            random_stratified_top20+=1-miss20;random_stratified_ps+=1-miss0
        result['replay']=dict(attempts=len(rows),valid=valid,all_chains_feasible=full,usable=usable,
            matched_count_uniform_top20=random_uniform_top20/len(rows),
            matched_valid_blocks_uniform_top20=random_stratified_top20/len(rows),
            matched_valid_blocks_uniform_ps=random_stratified_ps/len(rows),
            baseline_note='Analytic post-hoc diagnostic matching observed valid-block pattern; not an independent randomized trial')
    return result

if __name__=='__main__':
    import sys
    out={'independent_tiny_states_checked':brute_check(),'matrices':{}}
    for name in sys.argv[1:]:
        f=Path(name);r=check(f);out['matrices'][str(f)]=r
        print(str(f),r['status'],'gap',r['illegal_gap'],'worst_regret',r['original_ground_worst_regret'],r.get('replay'),flush=True)
    dest=ROOT/'artifacts/p2_research_20261128'/('packed_audit_'+sys.argv[1].split('/')[-2]+'.json')
    with dest.open('x') as f:json.dump(out,f,indent=2)
