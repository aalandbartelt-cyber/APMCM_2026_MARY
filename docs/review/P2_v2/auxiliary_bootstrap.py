"""Descriptive task bootstrap only. No sample-level independence or hypothesis tests."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'03_求解/D/p2_v2'))
from p2_common import OUT,REG,read,write_new

def main():
    frame=pd.read_csv(OUT/'results/sa_task_results.csv')
    seed=int(read(REG/'input_freeze.json')['plan_sha256'][:8],16)
    draw=np.random.default_rng(seed).integers(0,20,size=(5000,20))
    rows=[]
    for (ident,temp),part in frame.groupby(['id','temperature']):
        part=part.sort_values('block');assert len(part)==20
        for suffix in ('','_repaired'):
            feasible=part['n_feasible'+suffix].to_numpy()>0
            regret=part['best_regret'+suffix].to_numpy(float)
            success=feasible&(regret<=.1)
            rates=success[draw].mean(axis=1)
            conditional=[];empty=0
            for ix in draw:
                values=regret[ix][feasible[ix]]
                if len(values):conditional.append(float(np.median(values)))
                else:empty+=1
            interval=np.quantile(rates,[.025,.975])
            med=np.quantile(conditional,[.025,.975]).tolist() if conditional else [None,None]
            rows.append(dict(id=ident,temperature=temp,version='repaired' if suffix else 'raw',seed=seed,resamples=5000,
                task_success_fraction=float(success.mean()),descriptive_percentile_low=interval[0],descriptive_percentile_high=interval[1],
                boundary_degenerate='all_zero' if not success.any() else 'all_one' if success.all() else 'no',
                conditional_regret_empty_resamples=empty,conditional_regret_median_low=med[0],conditional_regret_median_high=med[1],
                interpretation='auxiliary description, 20 task blocks on one instance; not confirmatory inference'))
    pd.DataFrame(rows).to_csv(OUT/'results/auxiliary_task_bootstrap.csv',index=False)
    write_new(OUT/'results/bootstrap_protocol.json',dict(seed=seed,seed_rule='first eight hex digits of approved plan SHA256',resamples=5000,
        units='entire task blocks including feasibility indicators',CIM='not run; zero attempted tasks',claim='No CIM-versus-SA significance test'))
    print('Auxiliary descriptive bootstrap complete; empty/zero/one degeneracy retained.')

if __name__=='__main__':main()
