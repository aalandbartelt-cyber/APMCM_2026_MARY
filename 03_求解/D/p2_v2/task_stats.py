"""Closed task denominators; raw and repaired outputs never share success counts."""
import numpy as np
from scipy.stats import beta

STATES={'NOT_STARTED','SUBMISSION_FAILED','COMPUTATION_FAILED','PENDING','VALID_COMPLETED'}
def cp(k,n):
    if not n:return [None,None]
    return [0. if k==0 else float(beta.ppf(.025,k,n-k+1)),1. if k==n else float(beta.ppf(.975,k+1,n-k))]

def summarize(rows,repaired=False,grid=(0.,.1,.5,1.,2.,5.,10.,float('inf'))):
    assert len(rows)==20 and len({r['slot'] for r in rows})==20
    assert all(r['status'] in STATES for r in rows)
    suffix='_repaired' if repaired else ''
    na=sum(r['status']!='NOT_STARTED' for r in rows)
    valid=[r for r in rows if r['status']=='VALID_COMPLETED'];nv=len(valid)
    feasible=[r for r in valid if r.get('n_feasible'+suffix,0)>0];nf=len(feasible)
    assert all(np.isfinite(r['best_regret'+suffix]) and r['best_regret'+suffix]>=-1e-10 for r in feasible)
    hit=[r for r in feasible if r['best_regret'+suffix]<=.1];ne=len(hit)
    assert 0<=ne<=nf<=nv<=na<=20
    divide=lambda a,b:a/b if b else None
    values=[r['best_regret'+suffix] for r in feasible]
    return dict(version='repaired' if repaired else 'raw',N_A=na,N_V=nv,N_F=nf,N_epsilon=ne,
        submitted_fraction=na/20,valid_fraction=nv/20,end_to_end_success=divide(ne,na),
        conditional_hardware_success=divide(ne,nv),all_attempt_feasible=divide(nf,na),slot_success=ne/20,
        G20=[dict(threshold=x,value=sum(v<=x for v in values)/20) for x in grid],
        conditional_regret=values,conditional_regret_denominator=nf,
        binomial_interval_assumptions='Independent homogeneous task successes; fixed instance and cutoff. Auxiliary only.',
        conditional_task_CP95=cp(ne,nv),attempt_task_CP95=cp(ne,na),
        bootstrap_boundary='all_zero' if nv and ne==0 else 'all_one' if nv and ne==nv else 'no_valid_tasks' if not nv else None,
        statuses={s:sum(r['status']==s for r in rows) for s in sorted(STATES)})
