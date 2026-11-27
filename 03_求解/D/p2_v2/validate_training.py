"""Read-only model lineage and independent prediction reconstruction; zero fits."""
import sys
import json
import hashlib
import numpy as np
import pandas as pd
from scipy.special import expit
from p2_common import ROOT,P1,P23,OUT,write_new,read,sha,verify_inputs,now
sys.path.insert(0,str(ROOT/'03_求解/D/p1_v2'))
import common
import models

def main():
    verify_inputs();m=read(P23/'manifest.json')
    for name,h in m['files'].items():
        if name=='artifacts/p23_v2/training.log' and sha(ROOT/name)!=h:
            # The training process appends its completion message after manifest sealing.
            # Accept only this exact suffix; preserve the original manifest unchanged.
            content=(ROOT/name).read_bytes();suffix=b'{"done": true, "global_fits": 979}\n'
            assert content.endswith(suffix) and hashlib.sha256(content[:-len(suffix)]).hexdigest()==h
            closeout=OUT/'training_log_closeout.json'
            if not closeout.exists():write_new(closeout,dict(original_manifest_hash=h,closed_log_hash=sha(ROOT/name),appended_suffix=suffix.decode(),reason='Final stdout completion line follows model manifest; no model/data changes'))
        else:assert sha(ROOT/name)==h,name
    frames=[]
    for prefix in ('02','03'):
        d=common.load_data(prefix,True);d.id=prefix+':'+d.id.astype(str);frames.append(d)
    d=pd.concat(frames,ignore_index=True);bank=pd.read_pickle(P1/'features/F4.pkl')
    base=read(P23/'base.json');fold=common.fold_ids(d.ab,2,'calibration/0')
    metas={p.stem:read(p) for p in (P23/'models').glob('*.json')}
    assert len(metas)==65
    expected_base=[d,d.loc[fold!=0],d.loc[fold!=1],d.loc[d.gap==0],d.loc[d.gap>0]]
    starts=[r for r in common.Budget().entries() if r['event']=='start' and r.get('scope')=='P23_train02val03']
    successful={r['logical_id']:r['key'] for r in common.Budget().entries() if r['event']=='finish' and r.get('scope')=='P23_train02val03'}
    for i,frame in enumerate(expected_base,1):assert metas[successful[f'F{i:03d}']]['train_ids']==frame.id.tolist()
    groups=sorted(d.ab.unique());gr={a:np.flatnonzero(d.ab.to_numpy()==a) for a in groups}
    at=np.array([0,42,3000,len(bank)-1]);X=bank.iloc[at]
    def raw(key):
        mm=metas[key];assert mm['columns']==list(bank.columns) and mm['constant'] is None
        booster=models.lgb.Booster(model_file=str(P23/'models'/f'{key}.txt'))
        return booster.predict(X.to_numpy(float),raw_score=True,num_threads=4),mm
    gate0,gate1=base['calibration']['mapping'];reproduced=[]
    for b in range(20):
        saved=np.load(P23/'members'/f'member_{b:02d}.npz')
        draw=np.random.default_rng(211026+b).choice(groups,len(groups),replace=True)
        np.testing.assert_array_equal(saved['draw'],draw)
        bd=d.iloc[np.concatenate([gr[g] for g in draw])]
        specs=[bd,bd[bd.gap==0],bd[bd.gap>0]]
        for j,frame in enumerate(specs):assert metas[successful[f'F{6+3*b+j:03d}']]['train_ids']==frame.id.tolist()
        meta=read(P23/'members'/f'member_{b:02d}.json')
        z,gm=raw(meta['gate']);p=expit(np.clip(gate0+gate1*(z-gm['score_mean'])/gm['score_std'],-35,35))
        metal,_=raw(meta['metal']);nonmetal,_=raw(meta['nonmetal'])
        pred=(1-p)*(7.84+np.maximum(0,metal))+p*np.maximum(0,nonmetal)
        np.testing.assert_allclose(pred,saved['vhat'][at],rtol=0,atol=1e-12);reproduced.append(pred)
    u=np.load(P23/'universe.npz');np.testing.assert_array_equal(u['vhat'],u['members'].mean(axis=1))
    np.testing.assert_allclose(np.mean(reproduced,axis=0),u['vhat'][at],rtol=0,atol=1e-12)
    for a,b in [('07','11'),('08','12')]:
        pa=np.load(P23/f'pool_{a}.npz');pb=np.load(P23/f'pool_{b}.npz');mask=pb['allowed']
        np.testing.assert_array_equal(pa['vhat'][mask],pb['vhat'][mask]);np.testing.assert_array_equal(pa['members'][mask],pb['members'][mask])
    assert common.Budget().count()==m['global_fit_count']
    write_new(OUT/'training_validation.json',dict(time=now(),status='PASS',logical_models=65,fit_attempts=len(starts),global_fit_count=common.Budget().count(),
        checks=['frozen input and P1 protection','source-qualified train IDs','all two-fold calibration domains','20 exact AB bootstrap draws and multiplicities','all expert training domains','independent restored-model predictions','mean of complete member predictions','cross-pool bitwise equality','zero new fits']))
    print('PASS: 65 model lineages; 20 independent prediction reconstructions; no new fit.')

if __name__=='__main__':main()
