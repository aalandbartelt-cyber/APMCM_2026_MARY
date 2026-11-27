"""Exactly the approved P23 refit; reuse frozen P1 implementation, never its fits."""
import sys
import json
import numpy as np
import pandas as pd
from p2_common import ROOT,P1,P23,REG,DATA,write_new,read,sha,append,now,verify_inputs
sys.path.insert(0,str(ROOT/'03_求解/D/p1_v2'))
import common
import models

class Budget(common.Budget):
    logical_id=None
    def reserve(self,**metadata):
        assert self.logical_id
        old=[r for r in self.entries() if r.get('logical_id')==self.logical_id and r.get('scope')=='P23_train02val03' and r['event']=='start']
        retries=sum(r['event']=='start' and r.get('recovery_id') is not None for r in self.entries())
        if old: assert retries<21
        n=super().reserve(scope='P23_train02val03',logical_id=self.logical_id,
            recovery_id=f'R{retries+1:02d}' if old else None,**metadata)
        return n
    def append(self,row):
        row=dict(row,scope='P23_train02val03',logical_id=self.logical_id)
        super().append(row)
        append(P23/'fit_attempts.jsonl',row)

class Factory(models.Factory):
    def fit(self,indices,kind,**kwargs):
        if self.phase=='P23_base':
            if kind=='metal': number=4
            elif kind=='nonmetal': number=5
            elif len(indices)==len(self.data): number=1
            else:
                folds=common.fold_ids(self.data.ab,2,'calibration/0')
                number=2 if np.array_equal(np.sort(indices),np.flatnonzero(folds!=0)) else 3
                assert np.array_equal(np.sort(indices),np.flatnonzero(folds!=(number-2)))
        else:
            b=int(self.phase.rsplit('_',1)[1]);number=6+3*b+{'gate':0,'metal':1,'nonmetal':2}[kind]
        self.budget.logical_id=f'F{number:03d}'
        return super().fit(indices,kind,**kwargs)

def main():
    verify_inputs()
    assert not (P23/'manifest.json').exists(),'P23 already complete; do not refit'
    P23.mkdir(exist_ok=True)
    models.OUT=P23;models.Budget=Budget
    frames=[]
    for prefix in ('02','03'):
        d=common.load_data(prefix,True);d['source_id']=d.id;d['id']=prefix+':'+d.id.astype(str);frames.append(d)
    d=pd.concat(frames,ignore_index=True);assert len(d)==15225 and d.id.is_unique
    bank=pd.read_pickle(P1/'features/F4.pkl');assert bank.shape==(18928,336)
    X=bank.loc[d.key].set_axis(d.index);tr=d.index.to_numpy()
    fac=Factory(d,X,'F4','P23_base',tr)
    gate=fac.calibrate(tr,'gate')
    g=d.gap.to_numpy()>0
    metal=fac.fit(tr[~g],'metal');nonmetal=fac.fit(tr[g],'nonmetal')
    p=gate.predict(bank)
    full=(1-p)*(7.84+np.maximum(0,metal.predict(bank)))+p*np.maximum(0,nonmetal.predict(bank))
    basic=P23/'base.json'
    if not basic.exists():write_new(basic,dict(gate=gate.tree.meta['key'],calibration=gate.meta,metal=metal.meta['key'],nonmetal=nonmetal.meta['key']))
    np.save(P23/'single_full_predictions.npy',full)
    groups=sorted(d.ab.unique());group_rows={x:np.flatnonzero(d.ab.to_numpy()==x) for x in groups}
    dest=P23/'members';dest.mkdir(exist_ok=True)
    for b in range(20):
        target=dest/f'member_{b:02d}.npz'
        if target.exists():continue
        draw=np.random.default_rng(211026+b).choice(groups,len(groups),replace=True)
        ix=np.concatenate([group_rows[x] for x in draw])
        bd=d.iloc[ix].reset_index(drop=True);bx=X.iloc[ix].reset_index(drop=True);bi=bd.index.to_numpy()
        f=Factory(bd,bx,'F4',f'P23_bootstrap_{b}',bi)
        t=f.fit(bi,'gate');cg=models.Calibrated(t,gate.mapping,gate.meta)
        isg=bd.gap.to_numpy()>0
        m=f.fit(bi[~isg],'metal');n=f.fit(bi[isg],'nonmetal')
        prob=cg.predict(bank)
        v=(1-prob)*(7.84+np.maximum(0,m.predict(bank)))+prob*np.maximum(0,n.predict(bank))
        assert np.isfinite(v).all()
        np.savez_compressed(target,vhat=v,draw=draw)
        write_new(dest/f'member_{b:02d}.json',dict(gate=t.meta['key'],metal=m.meta['key'],nonmetal=n.meta['key'],seed=211026+b,calibration_sha256=sha(basic),prediction_sha256=sha(target)))
        print(json.dumps(dict(member=b,global_fits=common.Budget().count())),flush=True)
    members=np.column_stack([np.load(dest/f'member_{b:02d}.npz')['vhat'] for b in range(20)])
    mean=members.mean(axis=1)
    keys=np.array(bank.index,dtype=str)
    np.savez_compressed(P23/'universe.npz',keys=keys,members=members,vhat=mean,sd=members.std(axis=1,ddof=1),p05=np.quantile(members,.05,axis=1),p95=np.quantile(members,.95,axis=1))
    look={key:i for i,key in enumerate(keys)};A=sorted(d.A.unique());B=sorted(d.B.unique());ai={x:i for i,x in enumerate(A)};bj={x:i for i,x in enumerate(B)}
    for pool in ('07','08','11','12'):
        dd=common.load_data(pool);xs=[x for x in common.X_ORDER if x in set(dd.X)];xi={x:i for i,x in enumerate(xs)}
        w=np.full((52,52,len(xs)),np.nan);mask=np.zeros(w.shape,bool);mm=np.full(w.shape+(20,),np.nan)
        for row in dd.itertuples():
            at=(ai[row.A],bj[row.B],xi[row.X]);n=look[row.key];w[at]=mean[n];mm[at]=members[n];mask[at]=True
        assert mask.sum()==len(dd) and np.isnan(w[~mask]).all()
        np.savez_compressed(P23/f'pool_{pool}.npz',A=A,B=B,X=xs,vhat=w,allowed=mask,members=mm)
        dd['vhat']=[mean[look[k]] for k in dd.key];dd['model_scope']='P23_train02val03'
        dd['training_visible']=dd.key.isin(d.key)
        dd.to_csv(P23/f'pool_{pool}.csv',index=False,float_format='%.17g')
    ledger=common.Budget().entries();starts=[x for x in ledger if x['event']=='start' and x.get('scope')=='P23_train02val03']
    assert set(x['logical_id'] for x in starts)=={f'F{i:03d}' for i in range(1,66)}
    assert len(starts)<=86 and common.Budget().count()<=1000
    verify_inputs()
    write_new(P23/'manifest.json',dict(time=now(),scope='P23_train02val03',training_rows=len(d),features=336,members=20,logical_fits=65,actual_fit_attempts=len(starts),global_fit_count=common.Budget().count(),calibration='two AB OOF folds; one shared monotone sigmoid',files={str(p.relative_to(ROOT)):sha(p) for p in sorted(P23.rglob('*')) if p.is_file()},fixed_implementation={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'03_求解/D/p1_v2').glob('*.py')}))
    print(json.dumps(dict(done=True,global_fits=common.Budget().count())),flush=True)

if __name__=='__main__':main()
