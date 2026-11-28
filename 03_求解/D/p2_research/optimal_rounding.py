"""G01: full-state small-instance integer-rounding optimization, never hardware."""
from pathlib import Path
import os,json,itertools,hashlib,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/p2_research_20261128/rounding_G01'

def main():
    OUT.mkdir(exist_ok=False);n=10;pairs=list(itertools.combinations(range(n),2))
    S=np.c_[np.array(list(itertools.product([-1,1],repeat=n-1))),np.ones(2**(n-1),dtype=int)]
    A=np.array([-2*S[:,i]*S[:,j] for i,j in pairs]).T
    reg=dict(id='G01',purpose='Small-scale feasibility of optimizing floor/ceil choices; oracle ground states known by enumeration',
        n=10,reference_fixed=True,instances=12,seed=317720,bits=8,
        generation='random Gaussian couplings; tune edge(0,1) to a crossing plus signed 0.001 to produce a fragile gap',
        choice='each final Ising coefficient integer in [floor(scaled),ceil(scaled)], clipped[-127,127]',
        objective='maximize integer energy margin against every nonoptimal spin state',
        limits='60 seconds per instance; no retries; infeasible/timeout retained',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fits=0,hardware_calls=0)
    (OUT/'registration.json').write_text(json.dumps(reg,indent=2));rng=np.random.default_rng(317720);rows=[]
    for trial in range(12):
        coeff=rng.normal(0,10,size=len(pairs));coeff[0]=0;E0=A@coeff;plus=S[:,0]*S[:,1]==1
        crossing=(E0[plus].min()-E0[~plus].min())/4
        coeff[0]=crossing+(.001 if trial%2==0 else -.001)
        E=A@coeff;ground=np.flatnonzero(np.isclose(E,E.min(),rtol=0,atol=1e-9));assert len(ground)==1;g=int(ground[0])
        scale=127/np.abs(coeff).max();real=coeff*scale;nearest=np.rint(real).astype(int)
        lower=np.maximum(-127,np.floor(real));upper=np.minimum(127,np.ceil(real))
        diff=A-A[g];nonground=np.arange(len(S))!=g
        # diff @ k >= gap. Include all 511 competing states, not only feasible states.
        C=np.c_[diff[nonground],-np.ones(nonground.sum())];objective=np.r_[np.zeros(len(pairs)),-1.]
        t=time.monotonic();sol=milp(c=objective,integrality=np.r_[np.ones(len(pairs)),0],
            bounds=Bounds(np.r_[lower,-10000.],np.r_[upper,10000.]),
            constraints=LinearConstraint(C,0,np.inf),options={'time_limit':60.,'mip_rel_gap':0.})
        nearE=A@nearest;neararg=np.flatnonzero(nearE==nearE.min())
        row=dict(instance=trial,original_gap=float(np.sort(E)[1]-E.min()),
            scaled_gap=float(scale*(np.sort(E)[1]-E.min())),
            nearest_ground_count=len(neararg),nearest_all_ground_original=bool(np.all(neararg==g)),
            nearest_worst_original_regret=float(E[neararg].max()-E.min()),
            solver_status=int(sol.status),solver_message=sol.message,seconds=time.monotonic()-t)
        if sol.x is not None:
            k=np.rint(sol.x[:-1]).astype(int);assert np.all(k>=lower) and np.all(k<=upper)
            F=A@k;arg=np.flatnonzero(F==F.min());gap=int((F[nonground]-F[g]).min())
            row.update(optimized_gap=gap,optimized_ground_count=len(arg),optimized_all_ground_original=bool(np.all(arg==g)),
                optimized_worst_original_regret=float(E[arg].max()-E.min()),
                flipped_rounding_coefficients=int(np.sum(k!=nearest)))
            with (OUT/f'instance_{trial:02d}.npz').open('xb') as f:np.savez_compressed(f,original=coeff,nearest=nearest,optimized=k,pairs=np.array(pairs),states=S)
        rows.append(row);print(json.dumps(row),flush=True)
        with (OUT/f'instance_{trial:02d}.json').open('x') as f:json.dump(row,f,indent=2)
    with (OUT/'summary.json').open('x') as f:json.dump(rows,f,indent=2)

if __name__=='__main__':main()
