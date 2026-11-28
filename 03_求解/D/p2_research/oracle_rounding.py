"""G02 oracle control: directed rounding given a classically known optimum.

This encodes information about the already known optimum. It is NOT a discovery
algorithm and is excluded from any hardware-search claim or automatic selection.
"""
from pathlib import Path
import os,sys,json,hashlib,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/p2_research_20261128/oracle_G02'

def main():
    OUT.mkdir(exist_ok=False)
    src=ROOT/'artifacts/p2_dual_rescue/inputs/raw_J.npy';J=np.load(src);Q=np.load(ROOT/'artifacts/p2_dual_rescue/inputs/raw_Q.npy')
    z=np.load(ROOT/'artifacts/p23_v2/pool_11.npz');v=z['vhat'][:,:,0];mask=z['allowed'][:,:,0];R=float(np.ptp(v[mask]));lam=31.012015773309233
    ij=np.argwhere(mask);best=ij[np.argmin(v[mask])];star=-np.ones(105,dtype=int);star[best[0]]=star[52+best[1]]=star[-1]=1
    alpha=127/np.abs(J).max();scaled=alpha*J;prod=np.outer(star,star)
    K=np.where(prod==1,np.ceil(scaled),np.floor(scaled)).astype(np.int64);np.fill_diagonal(K,0)
    assert np.abs(K).max()<=127 and np.array_equal(K,K.T)
    # Reconstruct the exact symbolic raw nonnegative two-one-hot polynomial.
    C=np.where(mask,v-v[mask].min(),R);expected=np.zeros_like(Q);np.fill_diagonal(expected,-lam)
    for start in [0,52]:
        for i in range(start,start+52):
            for j in range(i+1,start+52):expected[i,j]=2*lam
    expected[:52,52:]=C;assert np.max(np.abs(Q-expected))<1e-12
    expectJ=np.zeros_like(J);off=expected+expected.T;np.fill_diagonal(off,0)
    expectJ[:-1,:-1]=-off/8;expectJ[:-1,-1]=expectJ[-1,:-1]=-(expected.sum(0)+expected.sum(1))/8
    # Whole-state energy perturbation bound for floating construction, not merely feasible-state checks.
    difference_bound=2*float(np.abs(expectJ-J).sum())
    true_gap=min(float(np.sort(v[mask])[1]-v[mask].min()),lam,R)
    assert true_gap>difference_bound
    err=K-scaled;assert np.all(err*prod>=-1e-12)
    X=np.zeros((2704,104),int)
    for i in range(52):
        for j in range(52):X[i*52+j,i]=X[i*52+j,52+j]=1
    S=np.c_[2*X-1,np.ones(2704,int)];E=-np.einsum('bi,ij,bj->b',S,K,S).reshape(52,52);ground=mask&(E==E[mask].min())
    reg=dict(id='G02',context='Oracle-assisted control after G01, not a candidate for autonomous search',
        known_optimum_indices=best.tolist(),input_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        rule='ceil(alpha J_ij) if s*_i s*_j=+1; floor otherwise',
        proof='Each disagreement edge increases E(s)-E(s*) by 4 times the nonnegative directed rounding error.',
        analytic_raw_gap_lower_bound=true_gap,float_gap_error_bound=difference_bound,
        claim='Ground-state preservation conditional on known original global optimum. Answer is already known classically.',
        attempts=100,seeds='320001..320100',iterations_per_t=10,alpha=.99,cutoff_ratio=.0001,
        initial_temperature='4 max absolute row sum',hardware_calls=0,fits=0)
    (OUT/'registration.json').write_text(json.dumps(reg,indent=2))
    with (OUT/'matrix.npz').open('xb') as f:np.savez_compressed(f,J=K,known_ground=star,scale=alpha)
    cert=dict(status='CERTIFIED_WITH_ORACLE',scope='Whole state space by analytic positive raw objective and directed-error proof',
        physical_spins=len(K),max_J=int(np.abs(K).max()),allowed_ground_count=int(ground.sum()),
        allowed_ground_worst_regret=float(v[ground].max()-v[mask].min()),
        allowed_second_gap=int(np.unique(E[mask])[1]-E[mask].min()),forbidden_onehot_gap=int(E[~mask].min()-E[mask].min()))
    (OUT/'certificate.json').write_text(json.dumps(cert,indent=2));print(json.dumps(cert),flush=True)
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'));from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def no_network(*a,**k):raise RuntimeError('Network prohibited during local SA')
    requests.sessions.Session.request=no_network
    scale=float(4*np.abs(K).sum(1).max());rows=[];start=time.monotonic()
    with (OUT/'raw.jsonl').open('x') as f:
        for i in range(100):
            row=dict(index=i,seed=320001+i)
            try:
                solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=scale,cutoff_temperature=scale*1e-4,alpha=.99,
                    iterations_per_t=10,size_limit=1,rand_seed=320001+i,process_num=1)
                a=np.asarray(solver.solve(K));assert a.shape==(1,len(K)) and np.isin(a,[-1,1]).all();s=a[0].astype(np.int64)
                x=(s[:-1]*s[-1]+1)//2;aa=np.flatnonzero(x[:52]);bb=np.flatnonzero(x[52:]);valid=len(aa)==len(bb)==1 and bool(mask[aa[0],bb[0]])
                row.update(status='VALID_COMPLETED',spins=s.tolist(),energy=int(-s@K@s),feasible=bool(valid),
                    regret=float(v[aa[0],bb[0]]-v[mask].min()) if valid else None)
            except Exception as e:row.update(status='FAILED',error=type(e).__name__+': '+str(e)[:200])
            rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
    summary=dict(attempts=100,valid=sum(r['status']=='VALID_COMPLETED' for r in rows),feasible=sum(r.get('feasible',False) for r in rows),
        ps=sum(r.get('regret')==0 for r in rows)/100,seconds=time.monotonic()-start,
        label='ORACLE CONTROL: previously known solution influences all rounding directions; not discovery evidence')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
