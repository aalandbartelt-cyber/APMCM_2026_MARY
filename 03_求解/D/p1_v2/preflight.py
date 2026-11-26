"""Input/feature audit and two counted, synthetic library parity fits."""
import json
import shutil
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from common import ROOT, OUT, CODE, Budget, load_data, verify_public_hashes, dump, sha, now


def prepare_library():
    target=OUT/'lightgbm_python/lightgbm'
    src=OUT/'sources/lightgbm-3.3.5/lightgbm'
    lib=OUT/'sources/lightgbm-3.3.5/compile/lib_lightgbm.so'
    assert lib.exists() and src.exists()
    if not target.exists():shutil.copytree(src,target)
    shutil.copy2(lib,target/'lib_lightgbm.so')
    return lib


def parity():
    result=OUT/'library_parity.json'
    if result.exists():
        assert json.loads(result.read_text())['passed'];return
    script='''import sys,json,numpy as np
if sys.argv[1] != "installed": sys.path.insert(0,sys.argv[1])
import lightgbm as lgb
rng=np.random.default_rng(210026);X=rng.normal(size=(96,5));y=(X[:,0]+X[:,1]>1).astype(int)
p=dict(objective="lambdarank",label_gain=[0,1],num_leaves=5,min_data_in_leaf=5,verbosity=-1,num_threads=4,deterministic=True,force_col_wise=True,seed=210026)
m=lgb.train(p,lgb.Dataset(X,label=y.astype(np.float32),group=np.array([96],dtype=np.int32)),num_boost_round=15)
print(json.dumps(dict(pred=m.predict(X).tolist(),version=lgb.__version__)))
'''
    values=[];budget=Budget()
    for name,arg in [('installed','installed'),('isolated',str(OUT/'lightgbm_python'))]:
        n=budget.reserve(phase='library_parity',target=name,n=96)
        try:
            proc=subprocess.run(['/usr/bin/python3.10','-c',script,arg],text=True,capture_output=True,check=True)
            values.append(json.loads(proc.stdout.strip().splitlines()[-1]))
            budget.append(dict(event='finish',fit_number=n))
        except Exception as e:
            detail=getattr(e,'stderr',repr(e))
            budget.append(dict(event='failed',fit_number=n,error=detail));print(detail,flush=True);raise
    diff=float(np.max(np.abs(np.array(values[0]['pred'])-values[1]['pred'])))
    dump(result,dict(passed=diff<1e-10,max_absolute_difference=diff,versions=[v['version'] for v in values]))
    assert diff<1e-10


def main():
    hashes=verify_public_hashes();lib=prepare_library();parity()
    existing=OUT/'preflight.json'
    if existing.exists():
        old=json.loads(existing.read_text())
        assert old['public_hashes']==hashes and old['library_sha256']==sha(lib)
        for name,digest in old['feature_hashes'].items():assert sha(OUT/'features'/name)==digest
        print(json.dumps(dict(preflight='verified existing immutable record',features=old['feature_dimensions'])))
        return
    from features import Features, STOICH, CHARGE
    d=load_data('02',True);val=load_data('03');test=load_data('04')
    assert not set(d.ab)&set(val.ab) and not set(d.ab)&set(test.ab) and not set(val.ab)&set(test.ab)
    assert (d.groupby('ab').size()==7).all()
    assert len(d)==11256 and sum(d.V<=2)==128 and not (d.V==0).any()
    assert (d.loc[d.gap==0,'V']>=7.84-1e-5).all()
    assert sum(v for v in STOICH['NO2'].values())==3
    universe=pd.concat([d[['id','A','B','X','ab','key']],val,test],ignore_index=True)
    assert len(universe)==18928 and universe.key.is_unique
    cache=OUT/'features';cache.mkdir(exist_ok=True)
    engine=Features(set(d.A)|set(d.B))
    f4=engine.transform(universe);f4.index=universe.key
    f0=engine.transform(universe,'F0');f0.index=universe.key
    masks={'F4':None,'F3':'E1','minus_electronic':'electronic','minus_geometry':'geometry','minus_xstats':'xstats'}
    tables={'F0':f0}
    for name,excluded in masks.items():
        tables[name]=f4 if excluded is None else f4[[c for c in f4 if excluded not in engine.tags[c]]]
    sample=universe.iloc[[0,9,500]]
    direct=engine.transform(sample).to_numpy()
    np.testing.assert_allclose(direct,f4.loc[sample.key].to_numpy(),equal_nan=True)
    swapped=sample.iloc[::-1]
    np.testing.assert_allclose(engine.transform(swapped).to_numpy(),direct[::-1],equal_nan=True)
    assert engine.table['Pd']['NsValence']==0
    assert not np.isinf(f4.to_numpy()).any()
    for name,frame in tables.items():frame.to_pickle(cache/(name+'.pkl'))
    universe.to_csv(cache/'composition_index.csv',index=False)
    engine.save_schema()
    # No validation/holdout physical columns have been loaded here.
    report=dict(time=now(),public_hashes=hashes,library_sha256=sha(lib),
        counts={'train':len(d),'val_composition_only':len(val),'holdout_composition_only':len(test)},
        feature_dimensions={k:v.shape[1] for k,v in tables.items()},
        feature_hashes={p.name:sha(p) for p in cache.glob('*.pkl')},
        all_ab_disjoint=True,full_grid_rows=len(universe),no_infinite_features=True,
        single_batch_order_invariant=True,zero_Pd_preserved=True,
        geometry_strict_available=float((f4['geo_strict_count']>0).mean()),
        geometry_proxy_available=float((f4['geo_proxy_count']>0).mean()),
        formula_input_only=True)
    dump(OUT/'preflight.json',report)
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
