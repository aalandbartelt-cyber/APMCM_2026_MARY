"""F01: complete allowed-table audits for bounded monotone cost quantization."""
from pathlib import Path
import json,hashlib,csv
import numpy as np
from shaping_experiment import FAMILIES
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/p2_research_20261128/coarse_F01'

def transformed(r,family):
    R=r.max();u=r/R
    if family=='linear':return u
    if family=='piecewise2':return np.where(r<=2,.75*r/2,.75+.25*(r-2)/(R-2))
    if family=='sqrt':return np.sqrt(u)
    if family=='log2':return np.log1p(r/2)/np.log1p(R/2)
    if family=='capped_log8':return np.log1p(np.minimum(r,8)/2)/np.log(5)
    if family=='rank_sqrt':return np.sqrt(np.searchsorted(np.unique(r),r)/(len(np.unique(r))-1))
    raise ValueError(family)

def main():
    OUT.mkdir(exist_ok=False)
    (OUT/'registration.json').write_text(json.dumps(dict(id='F01',pools=['07','11'],levels=[7,15,31,63,127],families=FAMILIES,
        purpose='Deterministic table audit, not solver search; every setting retained',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),hardware_calls=0,fits=0),indent=2))
    rows=[]
    for pool in ['07','11']:
        z=np.load(ROOT/f'artifacts/p23_v2/pool_{pool}.npz');v=z['vhat'][:,:,0][z['allowed'][:,:,0]];r=v-v.min();R=float(r.max())
        order=np.lexsort((np.arange(len(v)),v));top=set(order[:20]);r_sorted=r[order]
        for family in FAMILIES:
            u=transformed(r,family)
            for Q in [7,15,31,63,127]:
                q=np.rint(Q*u).astype(int);qo=q[order];assert np.all(np.diff(qo)>=0)
                picked=np.lexsort((np.arange(len(v)),q))[:20];boundary=np.sort(q)[19]
                ground=r[q==q.min()];distinct=np.unique(q)
                # Every tie is explicitly retained for the argmin guarantee.
                rows.append(dict(pool=pool,candidates=len(v),family=family,levels=Q,
                    original_R=R,original_second_gap=float(r_sorted[1]),cost_step_linear=R/Q if family=='linear' else '',
                    min_count=len(ground),worst_ground_regret=float(ground.max()),
                    business_integer_gap=int(distinct[1]-distinct[0]) if len(distinct)>1 else 0,
                    physical_energy_gap=4*int(distinct[1]-distinct[0]) if len(distinct)>1 else 0,
                    top20_overlap=len(top&set(picked))/20,twentieth_tie_layer_size=int(sum(q==boundary)),
                    original_regret_max_in_twentieth_layer=float(r[q==boundary].max()),
                    all_pairs_order_reversals=0,unique_levels=len(distinct)))
    with (OUT/'audit.csv').open('x') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps([r for r in rows if r['levels']==127],indent=2))

if __name__=='__main__':main()
