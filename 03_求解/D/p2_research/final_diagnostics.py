"""Enumeration-only diagnostics. No sampling, fitting, or matrix mutation."""
from pathlib import Path
import json,math
import numpy as np
from packed_checker import dp_chain
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'artifacts/p2_research_20261128'

def one(p):
    z=np.load(p/'matrix.npz');K=z['J'];q=z['q'];v=z['values']
    bs=json.loads((p/'blocks.json').read_text());legalgaps=[];badgaps=[];deg=1
    maps=[]
    for b in bs:
        ids=list(range(b['start'],b['stop']));sub=K[np.ix_(ids+[len(K)-1],ids+[len(K)-1])]
        good,bad=dp_chain(sub);es=[]
        for t in range(len(ids)+1):
            s=np.r_[np.ones(t,dtype=np.int64),-np.ones(len(ids)-t,dtype=np.int64),1]
            es.append(int(-s@sub@s))
        assert min(es)==good
        deg*=sum(e==good for e in es);higher=[e-good for e in es if e>good]
        if higher:legalgaps.append(min(higher))
        badgaps.append(bad-good);maps.append(b['mapping'])
    energyunit=4*math.gcd(*K[np.triu_indices(len(K),1)].tolist())
    fullgap=min(legalgaps+badgaps)
    covered=np.array(sum(maps,[]));vv=v[covered];uq=np.unique(q[covered]);uq.sort()
    # Exact, cost-independent stratified-uniform candidate baseline; each group
    # supplies one uniformly chosen candidate, followed by the same (q,index) decoder.
    prob=[]
    for g,group in enumerate(maps):
        for c in group:
            key=(q[c],c);pchoose=1/len(group)
            for h,other in enumerate(maps):
                if h!=g:pchoose*=sum((q[j],j)>key for j in other)/len(other)
            prob.append((c,pchoose))
    assert abs(sum(p for c,p in prob)-1)<1e-10
    ordered=sorted(covered,key=lambda c:(v[c],int(c)))
    iszero='zero' in p.name
    return dict(spins=len(K),groups=len(bs),declared_integer_coefficient_step=1,
        observed_coefficient_gcd=energyunit//4,
        lattice_energy_unit=energyunit,global_positive_excitation_gap=fullgap,
        global_gap_over_energy_lattice=fullgap/energyunit,
        illegal_gap=min(badgaps),legal_excitation_gap=min(legalgaps) if legalgaps else None,
        fixed_reference_ground_degeneracy=str(deg),unfixed_ground_degeneracy=str(2*deg),
        best_to_second_original_candidate_encoded_gap=0 if iszero else 4*int(q[ordered[1]]-q[ordered[0]]),
        best_to_next_distinct_q_energy_gap=0 if iszero else 4*int(uq[1]-uq[0]) if len(uq)>1 else None,
        decoder_only_q_gap=4*int(uq[1]-uq[0]) if len(uq)>1 else None,
        original_best_to_second_gap=float(np.sort(np.unique(vv))[1]-vv.min()),
        random_baseline=dict(type='Exact stratified uniform, one candidate per group, same (q,index) decoder; classical reference distribution, not hardware model',
            optimal_probability=sum(p for c,p in prob if v[c]==v.min()),
            regret_le_2_probability=sum(p for c,p in prob if v[c]-v.min()<=2),
            top20_probability=sum(p for c,p in prob if 1+sum(v<v[c])<=20)))

if __name__=='__main__':
    names=['short_H05/40_real','short_H05/40_zero','validation_H07_H08/blind_permutation_real',
        'validation_H07_H08/blind_linear']+[f'validation_H07_H08/full_batch{i}_real' for i in range(5)]
    out={n:one(BASE/n) for n in names}
    with (BASE/'energy_diagnostics_v2.json').open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps(out,indent=2))
