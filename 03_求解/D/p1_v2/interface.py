"""Build numeric tables plus explicit membership masks; no QUBO or solver calls."""
import json
import numpy as np
import pandas as pd
from common import OUT,X_ORDER,load_data,dump,sha,now


def main():
    dest=OUT/'interface';dest.mkdir(exist_ok=True)
    d=load_data('02');A=sorted(d.A.unique());B=sorted(d.B.unique())
    ai={a:i for i,a in enumerate(A)};bi={b:i for i,b in enumerate(B)}
    records=[]
    for prefix in ('07','08','11','12'):
        p=OUT/'predictions'/f'{prefix}_P1_train02_predictions.csv'
        frame=pd.read_csv(p,float_precision='round_trip');xs=[x for x in X_ORDER if x in set(frame.X)];xi={x:i for i,x in enumerate(xs)}
        values=np.full((len(A),len(B),len(xs)),np.nan);spread=values.copy();mask=np.zeros(values.shape,dtype=bool)
        for r in frame.itertuples():
            index=(ai[r.A],bi[r.B],xi[r.X]);assert not mask[index]
            mask[index]=True;values[index]=r.vhat;spread[index]=r.bootstrap_sd
        assert int(mask.sum())==len(frame)
        assert np.isfinite(values[mask]).all() and np.isnan(values[~mask]).all()
        path=dest/f'{prefix}_vhat_and_membership.npz'
        np.savez_compressed(path,A=np.array(A),B=np.array(B),X=np.array(xs),vhat=values,
            bootstrap_sd=spread,allowed=mask,model_scope=np.array('P1_train02'),score_kind=np.array('original_V_scale'))
        with np.load(path,allow_pickle=False) as check:
            np.testing.assert_array_equal(check['allowed'],mask)
            np.testing.assert_allclose(check['vhat'],values,rtol=0,atol=0,equal_nan=True)
        records.append(dict(pool=prefix,shape=list(values.shape),allowed_rows=int(mask.sum()),
            invalid_rows=int((~mask).sum()),file=path.name,sha256=sha(path),prediction_sha256=sha(p)))
    dump(dest/'manifest.json',dict(time=now(),tables=records,scope='P1_train02',
         invalid_value='NaN; membership mask must be enforced, never replace missing cost with zero',
         scope_transition='P23_train02val03 refit deferred',P2_logical_bits=104,P3_composite_logical_bits=208,
         P3_future_comparison=['3x104-bit','208-bit','HOBO quadratization'],solver_called=False))
    print(json.dumps(records))


if __name__=='__main__':main()
