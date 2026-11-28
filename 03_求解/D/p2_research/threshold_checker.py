"""Independent inverse-polynomial certificate for F02. No builder imports."""
from pathlib import Path
import hashlib, json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'artifacts/p2_research_20261128/threshold_F02'

def main():
    pool=np.load(ROOT/'artifacts/p23_v2/pool_11.npz');mask=pool['allowed'][:,:,0];v=pool['vhat'][:,:,0];R=v-v[mask].min()
    results={}
    for name,epsilon in [('eps01',.1),('eps2',2),('mask_only',float('inf'))]:
        z=np.load(BASE/name/'matrix.npz');K=z['J'];cost=z['cost']
        assert K.shape==(105,105) and K.dtype.kind in 'iu' and np.array_equal(K,K.T) and not np.diag(K).any() and abs(K).max()<=127
        # Expand -s^T K s under s_i=(2x_i-1)s_ref independently.
        diag=4*(K[:-1,:-1].sum(1)-K[:-1,-1]);off=-8*np.triu(K[:-1,:-1],1)
        assert np.array_equal(diag,np.full(104,-4))
        assert np.array_equal(off[:52,:52],np.triu(np.full((52,52),8),1))
        assert np.array_equal(off[52:,52:],np.triu(np.full((52,52),8),1))
        assert np.array_equal(off[:52,52:],8*cost)
        expected=np.where(mask&(R<=epsilon),0,1)
        assert np.array_equal(cost,expected) and np.isin(cost,[0,1]).all()
        zero=np.argwhere(cost==0);assert len(zero)>0 and all(mask[a,b] for a,b in zero)
        # E_K = 8*[x^T C y + .5*(a-1)^2 + .5*(b-1)^2] + fixed constant.
        # All summands nonnegative. Ground requires a=b=1,C_ab=0.
        worst=max(float(R[a,b]) for a,b in zero)
        r=dict(status='CERTIFIED' if worst<=.1 else 'COUNTEREXAMPLE',G1='CERTIFIED',
            G2_at_original_tolerance='CERTIFIED' if worst<=.1 else 'COUNTEREXAMPLE',
            ground_candidate_count=len(zero),worst_original_ground_regret=worst,
            G1_illegal_energy_gap_lower_bound=4,
            theorem='Inverse integer polynomial equals8 times nonnegative cost plus positive squared cardinality penalties; zero-cost allowed witness exists.',
            scope='COUNTEREXAMPLE when G2 fails refers to original0.1 gate, not G1; exploratory tolerance2 result is separate.',
            matrix_sha256=hashlib.sha256((BASE/name/'matrix.npz').read_bytes()).hexdigest())
        file=BASE/name/'raw.jsonl'
        if file.exists():
            rows=[json.loads(x) for x in file.read_text().splitlines()];assert len(rows)==100
            counts=dict(valid=0,feasible=0,hits=0,near2=0,top20=0)
            for row in rows:
                if row['status']!='VALID_COMPLETED':continue
                s=np.array(row['spins'],dtype=np.int64);assert s.shape==(105,) and np.isin(s,[-1,1]).all() and int(-s@K@s)==row['energy']
                counts['valid']+=1;s=s*s[-1];aa=np.flatnonzero(s[:52]>0);bb=np.flatnonzero(s[52:104]>0)
                feasible=len(aa)==len(bb)==1 and bool(mask[aa[0],bb[0]])
                assert feasible==row['feasible'];counts['feasible']+=feasible
                if feasible:
                    a,b=aa[0],bb[0];regret=float(R[a,b]);rank=int(1+np.count_nonzero(v[mask]<v[a,b]));assert regret==row['regret'] and rank==row['rank']
                    counts['hits']+=regret==0;counts['near2']+=regret<=2;counts['top20']+=rank<=20
            r['independent_replay']=counts
        results[name]=r
    with (BASE/'independent_certificate_replay.json').open('x') as f:json.dump(results,f,indent=2)
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
