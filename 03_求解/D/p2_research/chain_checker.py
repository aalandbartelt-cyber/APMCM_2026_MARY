"""Independent complete state-space DP on an archived chain-plus-reference matrix."""
from pathlib import Path
import json
import numpy as np

def check(file):
    z=np.load(file);K=z['J'];n=len(K)-1
    assert K.dtype.kind in 'iu' and np.array_equal(K,K.T) and not np.diag(K).any()
    assert np.abs(K).max()<=127 and n+1<=550
    for i in range(n):
        for j in range(i+2,n):assert K[i,j]==0
    # State=(last spin, has a 0->1 violation). Gauge-fix the reference to +1.
    dp={(s,False):(-2*int(K[0,n])*s,[s]) for s in [-1,1]}
    for i in range(1,n):
        next_dp={}
        for (prev,bad),(value,path) in dp.items():
            for s in [-1,1]:
                key=(s,bad or (prev==-1 and s==1))
                cost=value-2*int(K[i,n])*s-2*int(K[i-1,i])*prev*s
                if key not in next_dp or cost<next_dp[key][0]:next_dp[key]=(cost,path+[s])
        dp=next_dp
    good=min((v for (s,b),v in dp.items() if not b),key=lambda p:p[0])
    bad=min((v for (s,b),v in dp.items() if b),key=lambda p:p[0])
    for e,path in [good,bad]:
        spin=np.r_[path,1];assert -spin@K@spin==e
    legal_energies=[]
    for t in range(n+1):
        s=np.r_[np.ones(t,dtype=int),-np.ones(n-t,dtype=int),1]
        legal_energies.append(int(-s@K@s))
    E=np.asarray(legal_energies);q=z['q'];assert np.unique(E-4*q).size==1
    assert E.min()==good[0]
    original=z['values'][z['mapping']]
    return dict(status='CERTIFIED' if bad[0]>good[0] else 'COUNTEREXAMPLE',
        all_states_certified=f'2^{n} reference-fixed states (both gauges equivalent)',
        legal_states=len(E),legal_min=good[0],illegal_min=bad[0],illegal_gap=bad[0]-good[0],
        worst_ground_regret=float(original[E==E.min()].max()-z['values'].min()),
        integer_ground_multiplicity=int(np.sum(E==E.min())),
        illegal_min_witness=bad[1],ground_witness=good[1])

if __name__=='__main__':
    import sys
    file=Path(sys.argv[1]);result=check(file)
    with file.with_suffix('.certificate.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if 'witness' not in k},indent=2))
