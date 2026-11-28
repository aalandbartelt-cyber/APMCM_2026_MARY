"""E01: bounded stochastic-rounding audit; no SA, fitting, or hardware."""
from pathlib import Path
import datetime,hashlib,itertools,json,os
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/p2_research_20261128/rounding_E01'

def states(maxcard):
    rows=[np.zeros(52,dtype=np.int64)]
    for k in range(1,maxcard+1):
        for inds in itertools.combinations(range(52),k):
            r=np.zeros(52,dtype=np.int64);r[list(inds)]=1;rows.append(r)
    return np.array(rows)

def audit(K,v,mask):
    # Inverse polynomial, independently from the original QUBO builder.
    d=4*(K[:-1,:-1].sum(1)-K[:-1,-1]);Q=-8*np.triu(K[:-1,:-1],1);np.fill_diagonal(Q,d)
    A=states(2);B=states(1);ca=A.sum(1);cb=B.sum(1)
    legal=Q.diagonal()[:52,None]+Q.diagonal()[None,52:]+Q[:52,52:]
    best=legal[mask].min();win=mask&(legal==best);worst=float((v[win]-v[mask].min()).max())
    bestbad=float('inf');witness=None
    for aa,bb,ac,bc in [(A,B,ca,cb),(B,A,cb,ca)]:
        e=np.einsum('bi,ij,bj->b',aa,Q[:52,:52],aa)[:,None]+np.einsum('bi,ij,bj->b',bb,Q[52:,52:],bb)[None,:]+aa@Q[:52,52:]@bb.T
        valid=(ac[:,None]==1)&(bc[None,:]==1)
        # onehot choices start at row1, so mask placement is exact.
        valid[1:53,1:53]&=mask
        e=np.where(valid,np.inf,e);idx=np.unravel_index(np.argmin(e),e.shape)
        if e[idx]<bestbad:bestbad=float(e[idx]);witness=(np.flatnonzero(aa[idx[0]]).tolist(),np.flatnonzero(bb[idx[1]]).tolist())
    return dict(G1='COUNTEREXAMPLE' if bestbad<=best else 'UNKNOWN',G2_allowed_subspace='CERTIFIED' if worst<=.1 else 'COUNTEREXAMPLE',
        allowed_min=float(best),illegal_witness_energy=bestbad,illegal_minus_allowed=bestbad-float(best),witness_indices=witness,
        allowed_ground_count=int(win.sum()),allowed_worst_regret=worst,
        scope='All2704 onehot states audited; illegal search limited to cardinalities(0..2,0..1) union(0..1,0..2). Absence of witness is UNKNOWN.')

def main():
    OUT.mkdir(exist_ok=False)
    (OUT/'registration.json').write_text(json.dumps(dict(id='E01',time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        design='32 independent unbiased upper-edge stochastic roundings for each frozen raw/rc floating J; no lambda change.',
        seeds='370001..370032',range=127,early_stop=False,SA_calls=0,hardware_calls=0,
        auxiliary='Six disjoint five-matrix arithmetic means in perfectly aligned-copy subspace. Fractional means are diagnostics, not valid single int8 matrices; alignment proof not claimed.',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2))
    pool=np.load(ROOT/'artifacts/p23_v2/pool_11.npz');v=pool['vhat'][:,:,0];mask=pool['allowed'][:,:,0];result={}
    for encoding in ['raw','rc']:
        J=np.load(ROOT/f'artifacts/p2_dual_rescue/inputs/{encoding}_J.npy');alpha=127/abs(J).max();upper=np.triu_indices(len(J),1);x=alpha*J[upper];low=np.floor(x);frac=x-low;matrices=[];trials=[]
        for i in range(32):
            rng=np.random.default_rng(370001+i);a=(low+(rng.random(len(x))<frac)).astype(np.int64);K=np.zeros_like(J,dtype=np.int64);K[upper]=a;K+=K.T
            assert abs(K).max()<=127
            with (OUT/f'{encoding}_{i:02d}.npy').open('xb') as f:np.save(f,K)
            trials.append(dict(seed=370001+i,**audit(K,v,mask)));matrices.append(K)
        averaged=[audit(np.mean(matrices[5*b:5*b+5],axis=0),v,mask) for b in range(6)]
        result[encoding]=dict(trials=trials,aligned_five_copy_diagnostics=averaged,
            independent_rounding_variance_upper_edge_sum=float(np.sum(frac*(1-frac))),
            no_shared_reference_physical_spins_for5=5*len(J),
            note='Fivecopies fit525 spins but coupling consistency penalties are not supplied or certified. Averaging objectives differs from selecting the best of independently minimized matrices.')
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:{'G1_counterexamples':sum(x['G1']=='COUNTEREXAMPLE' for x in d['trials']),
        'allowed_G2_pass':sum(x['G2_allowed_subspace']=='CERTIFIED' for x in d['trials']),
        'worst_regret_range':[min(x['allowed_worst_regret'] for x in d['trials']),max(x['allowed_worst_regret'] for x in d['trials'])],
        'mean5_G1_counterexamples':sum(x['G1']=='COUNTEREXAMPLE' for x in d['aligned_five_copy_diagnostics']),
        'mean5_G2_pass':sum(x['G2_allowed_subspace']=='CERTIFIED' for x in d['aligned_five_copy_diagnostics'])} for k,d in result.items()},indent=2))

if __name__=='__main__':main()
