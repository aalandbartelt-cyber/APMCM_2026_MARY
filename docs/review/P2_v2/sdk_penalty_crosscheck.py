"""Reproduce the registered SDK penalty diagnostic; never changes selected lambda."""
from pathlib import Path
import sys,csv
import numpy as np
import kaiwu as kw
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'03_求解/D/p2_v2'))
from p2_common import P23,OUT

def main():
    rows=[]
    for pool in ('07','11'):
        z=np.load(P23/f'pool_{pool}.npz');W=z['vhat'][:,:,0];mask=z['allowed'][:,:,0]
        m=W[mask].min();R=W[mask].max()-m;C=np.where(mask,W-m,R if R else 1.)
        for enc in ('raw','rc'):
            u=C.min(axis=1) if enc=='rc' else np.zeros(52);v=(C-u[:,None]).min(axis=0) if enc=='rc' else np.zeros(52)
            D=C-u[:,None]-v[None,:];a=[kw.core.Binary(f'a{i}') for i in range(52)];b=[kw.core.Binary(f'b{i}') for i in range(52)]
            obj=kw.core.quicksum([float(D[i,j])*a[i]*b[j] for i in range(52) for j in range(52)])+kw.core.quicksum([float(u[i])*a[i] for i in range(52)])+kw.core.quicksum([float(v[j])*b[j] for j in range(52)])
            for name,var in [('A',a),('B',b)]:
                c=kw.core.quicksum(var)-1
                rows.append(dict(pool=pool,encoding=enc,constraint=name,analytic_main_lambda=1.1*(R if R else 1.),sdk_general_squared=kw.core.get_min_penalty(obj,c**2),sdk_equal_linear=kw.core.get_min_penalty_for_equal_constraint(obj,c)))
    with (OUT/'results/sdk_penalty_crosscheck.csv').open('x') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

if __name__=='__main__':main()
