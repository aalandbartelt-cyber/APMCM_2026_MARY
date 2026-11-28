"""Independent H05/H07/H08 matrix certificate and raw-state replay."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'03_求解/D/p2_research'))
from packed_checker import dp_chain,brute_check
from replay_audit import replay,read_rows
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'artifacts/p2_research_20261128'

def certify(p):
    z=np.load(p/'matrix.npz');K=z['J'];q=z['q'];v=z['values'];blocks=json.loads((p/'blocks.json').read_text());n=len(K)-1
    source=np.load(ROOT/f'artifacts/p23_v2/pool_{"07" if len(v)==2704 else "11"}.npz')
    expected_values=source['vhat'][:,:,0][source['allowed'][:,:,0]]
    assert np.array_equal(v,expected_values)
    rr=expected_values-expected_values.min();span=rr.max()
    expected_q=np.rint(63*(rr/span if 'linear' in p.name else np.where(rr<=2,.375*rr,.75+.25*(rr-2)/(span-2)))).astype(np.int64)
    assert np.array_equal(q,expected_q)
    assert len(K)<=550 and K.dtype.kind in 'iu' and abs(K).max()<=127 and np.array_equal(K,K.T) and not np.diag(K).any()
    edges=np.zeros_like(K,dtype=bool);covered=[];mapped=[];gaps=[];mins=[];ground_candidates=[]
    iszero='zero' in p.name
    for b in blocks:
        assert b['reference'] == n, 'Reference index mismatch'
        assert all(isinstance(i,int) and 0 <= i < len(v) for i in b['mapping']), 'Candidate index outside dictionary'
        ids=list(range(b['start'],b['stop']));covered+=ids;mapped+=b['mapping'];assert len(b['mapping'])==len(ids)+1
        for a,c in zip(ids[:-1],ids[1:]):edges[a,c]=edges[c,a]=True
        edges[ids,n]=edges[n,ids]=True
        sub=K[np.ix_(ids+[n],ids+[n])];good,bad=dp_chain(sub);es=[]
        for t in range(len(ids)+1):
            s=np.r_[np.ones(t,dtype=np.int64),-np.ones(len(ids)-t,dtype=np.int64),1];es.append(int(-s@sub@s))
        costs=np.zeros(len(es),dtype=int) if iszero else q[b['mapping']]
        assert np.unique(np.array(es)-4*costs).size==1 and min(es)==good
        gaps.append(bad-good);mins.append(good);ground_candidates += [b['mapping'][i] for i,e in enumerate(es) if e==good]
    if len(v)==529: assert sorted(mapped)==list(range(529)), 'Incomplete blind dictionary'
    assert covered==list(range(n)) and len(set(mapped))==len(mapped) and not K[~edges].any()
    # Global decoder min(q,index) across block minimizers: only blocks attaining
    # the minimum q in this batch can win. Enumerate all their tied candidates.
    bestq=min(q[c] for c in mapped)
    winners=[c for c in ground_candidates if q[c]==bestq]
    assert winners
    worst=max(float(v[c]-v[mapped].min()) for c in winners)
    zero_witness=[max(b['mapping'],key=lambda c:(q[c],c)) for b in blocks] if iszero else []
    zero_selected=min(zero_witness,key=lambda c:(q[c],c)) if iszero else None
    zero_regret=float(v[zero_selected]-v[mapped].min()) if iszero else None
    if iszero:assert zero_regret>.1
    result=dict(G1='CERTIFIED' if min(gaps)>0 else 'COUNTEREXAMPLE',
        G2='CERTIFIED' if not iszero and worst<=.1 else 'COUNTEREXAMPLE',
        spins=len(K),max_J=int(abs(K).max()),illegal_gap=min(gaps),ground_energy=sum(mins),
        batch_candidates=len(mapped),batch_min_value=float(v[mapped].min()),batch_ground_worst_regret=None if iszero else worst,
        zero_control_ground_counterexample_regret=zero_regret,zero_control_witness_candidate_per_chain=zero_witness,
        global_min_value=float(v.min()),mapped_candidates=mapped,
        matrix_sha256=hashlib.sha256((p/'matrix.npz').read_bytes()).hexdigest())
    if (p/'raw.jsonl').exists():
        rows=read_rows(p/'raw.jsonl');assert len(rows)==100
        result['replay']=replay(K,q,v,blocks,rows)
    return result

def main(mode):
    root=BASE/('short_H05' if mode=='h05' else 'validation_H07_H08')
    results={p.name:certify(p) for p in sorted(root.iterdir()) if p.is_dir() and (p/'matrix.npz').exists()}
    if mode!='h05':
        covered=sum([results[f'full_batch{i}_real']['mapped_candidates'] for i in range(5)],[])
        assert sorted(covered)==list(range(2704))
        for i,expected in enumerate(np.array_split(np.arange(2704),5)):
            for kind in ('real','zero'):
                assert sorted(results[f'full_batch{i}_{kind}']['mapped_candidates'])==expected.tolist()
    report=dict(independent_small_states=brute_check(),matrices=results)
    for x in results.values():del x['mapped_candidates']
    path=ROOT/'codex/p2_zero'/('replay_'+mode+'.json')
    with path.open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps({name:{k:v for k,v in d.items() if k in ['G1','G2','spins','max_J','illegal_gap','batch_ground_worst_regret','replay']} for name,d in results.items()},indent=2))

if __name__=='__main__':main(sys.argv[1])
