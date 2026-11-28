"""Independent G02 certificate using exact rational arithmetic on stored floats.

No construction module imports; the known-answer condition is mandatory.
"""
from fractions import Fraction as F
from pathlib import Path
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'artifacts/p2_research_20261128'

def main():
    z=np.load(BASE/'oracle_G02/matrix.npz');K=z['J'];s=z['known_ground'];alpha=F(float(z['scale']))
    J=np.load(ROOT/'artifacts/p2_dual_rescue/inputs/raw_J.npy')
    p=np.load(ROOT/'artifacts/p23_v2/pool_11.npz');v=p['vhat'][:,:,0];mask=p['allowed'][:,:,0]
    coords=np.argwhere(mask);best=coords[np.argmin(v[mask])];vmin=float(v[mask].min())
    assert np.array_equal(np.flatnonzero(s[:-1]==1),[best[0],52+best[1]]) and s[-1]==1
    assert K.dtype.kind in 'iu' and abs(K).max()<=127 and np.array_equal(K,K.T) and not np.diag(K).any()
    jf=[[F(float(a)) for a in row] for row in J]
    lam=F(31.012015773309233);span=F(float(np.ptp(v[mask])))
    error=F(0);directed_min=None;adverse=F(0);negative_edges=0
    for i in range(104):
        got=4*sum(jf[i][j] for j in range(104) if j!=i)-4*jf[i][104]
        error+=abs(got+lam)
        for j in range(i+1,104):
            got=-8*jf[i][j]
            expected=2*lam if (i<52)==(j<52) else (F(float(v[i,j-52]-vmin)) if mask[i,j-52] else span)
            error+=abs(got-expected)
    positive=[F(float(x-vmin)) for x in v[mask] if x>vmin]
    theoretical_gap=min(min(positive),lam,span)
    assert theoretical_gap>2*error
    for i in range(105):
        for j in range(i+1,105):
            e=(F(int(K[i,j]))-alpha*jf[i][j])*int(s[i]*s[j])
            directed_min=e if directed_min is None else min(directed_min,e)
            if e<0:adverse-=4*e;negative_edges+=1
    certified_gap=alpha*(theoretical_gap-2*error)-adverse
    assert certified_gap>0
    r=dict(G1='CERTIFIED',G2='CERTIFIED',condition='ORACLE: known original optimum used to direct rounding; excluded from autonomous hardware-search selection',
        arithmetic='Exact fractions for stored float coefficients and alpha',
        raw_polynomial_gap_lower_bound=float(theoretical_gap),pairwise_float_gap_error_bound=float(2*error),
        minimum_directed_rounding_error=float(directed_min),
        negative_directed_edges_from_floating_product=negative_edges,
        total_adverse_gap_bound=float(adverse),certified_all_state_gap_lower_bound=float(certified_gap),
        theorem='For every original nonoptimal state, the scaled original gap minus polynomial float error and the sum of all adverse rounding edges remains strictly positive. Unique original ground modulo global sign is retained.',
        correction='Initial checker assumed exact nonnegative per-edge errors, which finite-precision alpha*J need not satisfy. Original failed checker and error record retained; final proof uses exact fractions and a global adverse bound.')
    with (BASE/'oracle_G02/independent_exact_certificate.json').open('x') as f:json.dump(r,f,indent=2)
    print(json.dumps(r,indent=2))

if __name__=='__main__':main()
