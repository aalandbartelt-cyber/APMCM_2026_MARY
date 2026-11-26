"""Registered experiments with resumable domain-level checkpoints."""
import argparse
import json
import os
import time
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from common import (ROOT,OUT,CODE,DATA,EPS,SEED,X_ORDER,ROUTES,REG,load_data,fold_ids,
                    stable,dump,sha,now,Budget,code_hashes,verify_public_hashes)
from models import Factory,Bundle,Calibrated,Tree
from metrics import evaluate,select,ordered,reliability_rows


class Experiment:
    def __init__(self):
        assert json.loads((OUT/'preflight.json').read_text())['formula_input_only']
        self.d=load_data('02',True)
        self.bank={p.stem:pd.read_pickle(p) for p in (OUT/'features').glob('*.pkl')}
        self.X={k:v.loc[self.d.key].set_axis(self.d.index) for k,v in self.bank.items()}
        self.outer=fold_ids(self.d.ab,5,'outer/0')
        self.parts=OUT/'domains';self.parts.mkdir(exist_ok=True)
        self.splits={}
        self.register()

    def register(self):
        d=self.d
        for f in range(5):
            tr=np.flatnonzero(self.outer!=f);te=np.flatnonzero(self.outer==f)
            self.splits[f'main_outer_{f}']=(tr,te)
            inner=fold_ids(d.loc[tr,'ab'],3,f'inner/{f}')
            for j in range(3):self.splits[f'main_inner_{f}_{j}']=(tr[inner!=j],tr[inner==j])
        elems=sorted(set(d.A)|set(d.B));block=fold_ids(elems,5,'elements')
        for f in range(5):
            held={e for e,b in zip(elems,block) if b==f}
            test=d.A.isin(held)|d.B.isin(held)
            self.splits[f'element_{f}']=(np.flatnonzero(~test),np.flatnonzero(test))
        for x in X_ORDER:
            for f in range(5):
                self.splits[f'xleave_{x}_{f}']=(np.flatnonzero((d.X!=x)&(self.outer!=f)),np.flatnonzero((d.X==x)&(self.outer==f)))
        all_ab=set(d.ab)
        for t in (.5,1.,2.):
            target=set(d.loc[d.V<t,'ab'])
            background=sorted(all_ab-target,key=lambda a:stable(a,f'target/{t}'))
            held=target|set(background[:max(0,int(np.ceil(.2*len(all_ab)))-len(target))])
            test=d.ab.isin(held)
            self.splits[f'target_{t:g}']=(np.flatnonzero(~test),np.flatnonzero(test))
        for r in (1,2):
            repeat=fold_ids(d.ab,5,f'outer/{r}')
            for f in range(5):self.splits[f'repeat_{r}_{f}']=(np.flatnonzero(repeat!=f),np.flatnonzero(repeat==f))
        for name,(tr,te) in self.splits.items():
            assert not set(d.loc[tr,'ab'])&set(d.loc[te,'ab']),name
        manifest={'time':now(),'eps':EPS,'k':20,'utility_tau':2.,'capacity':'15 leaves/400 rounds/4 threads; conditional 7 leaves',
                  'model_menu':ROUTES,'expected_fit_upper_bound':992,'hard_fit_limit':1000,
                  'public_hashes':verify_public_hashes(),
                  'core_code_hashes':{p.name:sha(p) for p in [CODE/x for x in ('common.py','features.py','models.py','metrics.py','experiment.py')]},
                  'plan_sha256':sha(ROOT/'codex/P1_PLANv2.md'),
                  'preflight_sha256':sha(OUT/'preflight.json'),
                  'query_seeds':[0,1,2],'selection_ties':'EF,NDCG,regret,complexity,id; RMSE,MAE,complexity,id',
                  '03_access':'composition before selection; labels once for frozen batch; historical development exposure disclosed',
                  '04_access':'composition only; no hidden labels; no split reconstruction',
                  'statistical_family':'all main outer candidate-by-fold k20 tests; pooled OOF and 03 separate exploratory families'}
        freeze=OUT/'experiment_freeze.json'
        if freeze.exists():
            old=json.loads(freeze.read_text())
            for k in ('core_code_hashes','public_hashes','plan_sha256','preflight_sha256'):assert old[k]==manifest[k],f'Frozen {k} changed'
        else:
            dump(freeze,manifest)
            dump(OUT/'splits.json',{k:dict(train=self.d.loc[v[0],'id'].tolist(),test=self.d.loc[v[1],'id'].tolist()) for k,v in self.splits.items()})

    def domain(self,name,tr,te,routes=ROUTES,feature='F4',protocol=None):
        checkpoint=self.parts/(name+'.json')
        if checkpoint.exists():return json.loads(checkpoint.read_text())['metrics']
        start=time.monotonic();protocol=protocol or name.split('_')[0]
        fac=Factory(self.d,self.X[feature],feature,name,tr,te)
        bundle=Bundle(fac,tr,routes);predictions=bundle.predict(self.X[feature].loc[te])
        dd=self.d.loc[te];frames=[];rows=[];reliability=[]
        for route,pred in predictions.items():
            row=dict(protocol=protocol,domain=name,feature_set=feature,route=route,**evaluate(dd,pred));rows.append(row)
            frame=dd[['id','A','B','X','ab','key','V','gap']].copy();frame['row_index']=te
            for k,v in pred.items():frame[k]=v
            frame['route']=route;frame['domain']=name;frames.append(frame)
            reliability.extend(reliability_rows(dd,pred,route,protocol,name))
            # Descriptive per-X diagnostics, never used to change the menu.
            for x in sorted(dd.X.unique()):
                mask=dd.X.to_numpy()==x
                rows.append(dict(protocol=protocol+'_by_X',domain=name,feature_set=feature,route=route,X=x,
                                 **evaluate(dd.loc[mask],{k:np.asarray(v)[mask] for k,v in pred.items()})))
        pd.concat(frames).to_csv(self.parts/(name+'.csv.gz'),index=False)
        pd.DataFrame(reliability).to_csv(self.parts/(name+'_reliability.csv.gz'),index=False)
        dump(checkpoint,dict(metrics=rows,bundle=bundle.export(),train_n=len(tr),test_n=len(te),seconds=time.monotonic()-start))
        main=[r for r in rows if r['protocol']==protocol]
        print(json.dumps(dict(done=name,fits=Budget().count(),seconds=round(time.monotonic()-start,2),
                             results=[dict(route=r['route'],rmse=r.get('RMSE'),hits20=r['hits@20']) for r in main])),flush=True)
        return rows

    def main(self):
        selections=[]
        for f in range(5):
            inner=[]
            for j in range(3):
                name=f'main_inner_{f}_{j}'
                inner.extend(r for r in self.domain(name,*self.splits[name],protocol='inner') if r['protocol']=='inner')
            numeric=select(inner,'regression');screen=select(inner,'screening')
            name=f'main_outer_{f}'
            rows=[r for r in self.domain(name,*self.splits[name],protocol='outer') if r['protocol']=='outer']
            selections.append(dict(fold=f,numeric=numeric,screen=screen,
                numeric_result=next(r for r in rows if r['route']==numeric),screen_result=next(r for r in rows if r['route']==screen)))
            for feature in ('F0','F3'):
                self.domain(f'feature_{feature}_{f}',*self.splits[name],routes=['R-log'],feature=feature,protocol='feature')
            self.baselines(f,*self.splits[name])
            for seed in (1,2):self.hash_diagnostic(f,seed,*self.splits[name])
        dump(OUT/'nested_selection_results.json',selections)
        allrows=[]
        for f in range(5):
            allrows.extend(r for r in json.loads((self.parts/f'main_outer_{f}.json').read_text())['metrics'] if r['protocol']=='outer')
        dump(OUT/'02_nominees.json',dict(numeric=select(allrows,'regression'),screen=select(allrows,'screening'),
                                       selection_basis='02 outer descriptive comparison; nested procedure estimates stored separately'))

    def baselines(self,f,tr,te):
        dest=self.parts/f'baseline_{f}.json'
        if dest.exists():return
        d=self.d
        enc=pd.get_dummies(d.loc[tr,['A','B','X']],dtype=float)
        tst=pd.get_dummies(d.loc[te,['A','B','X']],dtype=float).reindex(columns=enc.columns,fill_value=0)
        ridge=Ridge(alpha=1.).fit(enc,d.loc[tr,'V'])
        predictions={'mean':np.full(len(te),d.loc[tr,'V'].mean()),'additive_ridge':ridge.predict(tst)}
        rows=[]
        for name,v in predictions.items():
            vv=np.maximum(0,v);rows.append(dict(protocol='baseline',domain=f'baseline_{f}',route=name,
                                                **evaluate(d.loc[te],dict(vhat_raw=v,vhat=vv,score=-vv))))
        score=np.array([int(stable(k,'random_baseline')[:13],16)/16**13 for k in d.loc[te,'key']])
        rows.append(dict(protocol='baseline',domain=f'baseline_{f}',route='random_hash',**evaluate(d.loc[te],dict(score=score),score_probability=False)))
        dump(dest,dict(metrics=rows,non_tree_fits=1))

    def hash_diagnostic(self,f,seed,tr,te):
        name=f'query_seed_{seed}_{f}';dest=self.parts/(name+'.json')
        if dest.exists():return
        fac=Factory(self.d,self.X['F4'],'F4',name,tr,te)
        tree=fac.fit(tr,'rank_hash4',query_seed=seed)
        score=tree.predict(self.X['F4'].loc[te])
        # No cross-fold probability interpretation for extra seeds.
        metrics=evaluate(self.d.loc[te],dict(score=score),score_probability=False)
        base=pd.read_csv(self.parts/f'main_outer_{f}.csv.gz')
        base=base[base.route=='L-hash4'].set_index('key').loc[self.d.loc[te,'key']]
        top=set(self.d.loc[te].iloc[ordered(score,self.d.loc[te,'key'])[:20]].key)
        top0=set(base.iloc[ordered(base.score,base.index)[:20]].index)
        union=len(top|top0)
        frame=self.d.loc[te,['id','key']].copy();frame['score']=score;frame.to_csv(self.parts/(name+'.csv.gz'),index=False)
        dump(dest,dict(metrics=[dict(protocol='query_seed',domain=name,route=f'L-hash4-seed{seed}',
                      top20_overlap=len(top&top0),top20_jaccard=len(top&top0)/union,**metrics)]))

    def stress(self):
        for name,pair in self.splits.items():
            if name.startswith(('element_','xleave_','target_')):
                self.domain(name,*pair,routes=['R-log','S-eps'],protocol=name.split('_')[0])

    def choose_final(self):
        if (OUT/'final_selection.json').exists():return json.loads((OUT/'final_selection.json').read_text())
        nominees=json.loads((OUT/'02_nominees.json').read_text())
        routes=list(dict.fromkeys([nominees['numeric'],nominees['screen'],'H-soft']))
        assert len(routes)<=3
        tr=self.d.index.to_numpy();fac=Factory(self.d,self.X['F4'],'F4','final_02',tr)
        bundle=Bundle(fac,tr,routes)
        export=bundle.export()
        dump(OUT/'03_candidate_freeze.json',dict(time=now(),routes=routes,models=export,fit_count=Budget().count(),
             model_hashes={v['tree_key']:sha(OUT/'models'/(v['tree_key']+'.json')) for v in export.values()}))
        # The only 03-label reading gate in the experiment implementation.
        d=load_data('03',True)
        assert not set(d.ab)&set(self.d.ab)
        xx=self.bank['F4'].loc[d.key]
        pred=bundle.predict(xx);rows=[];frames=[];reliability=[]
        for r,p in pred.items():
            rows.append(dict(protocol='03_development',domain='03',feature_set='F4',route=r,**evaluate(d,p)))
            frame=d.copy()
            for col,vals in p.items():frame[col]=vals
            frame['route']=r;frames.append(frame)
            reliability.extend(reliability_rows(d,p,r,'03_development','03'))
        pd.concat(frames).to_csv(OUT/'03_frozen_candidates.csv.gz',index=False)
        pd.DataFrame(reliability).to_csv(OUT/'03_reliability.csv',index=False)
        dump(OUT/'03_results.json',rows)
        result=dict(time=now(),numeric=select(rows,'regression'),screen=select(rows,'screening'),
                    candidates=routes,models=export,role='development selection, not an independent test',
                    candidate_freeze_sha256=sha(OUT/'03_candidate_freeze.json'),
                    next_steps_cannot_reselect=True)
        dump(OUT/'final_selection.json',result)
        print(json.dumps(dict(final_numeric=result['numeric'],final_screen=result['screen'],fits=Budget().count())),flush=True)
        return result

    def diagnostics(self):
        final=self.choose_final();routes=list(dict.fromkeys([final['numeric'],final['screen']]))
        for feature in ('minus_electronic','minus_geometry','minus_xstats'):
            for f in range(5):self.domain(f'ablation_{feature}_{f}',*self.splits[f'main_outer_{f}'],routes=routes,feature=feature,protocol='ablation')
        for name,pair in self.splits.items():
            if name.startswith('repeat_'):self.domain(name,*pair,routes=routes,protocol='repeat')
        self.bootstrap(final)

    def get_final_bundle(self,final):
        # All fits should be cache hits after the 03 gate; no 03 labels loaded.
        fac=Factory(self.d,self.X['F4'],'F4','final_cache_restore',self.d.index.to_numpy())
        return Bundle(fac,self.d.index.to_numpy(),list(dict.fromkeys([final['numeric'],final['screen']])))

    def bootstrap(self,final):
        dest=OUT/'bootstrap';dest.mkdir(exist_ok=True)
        base=self.get_final_bundle(final);route=final['numeric']
        groups=sorted(self.d.ab.unique());full=self.bank['F4'];done=[]
        for b in range(20):
            path=dest/f'member_{b:02d}.csv.gz'
            if path.exists():done.append(path.name);continue
            rng=np.random.default_rng(SEED+1000+b)
            draw=rng.choice(groups,size=len(groups),replace=True)
            group_rows={g:np.flatnonzero(self.d.ab.to_numpy()==g) for g in groups}
            bootix=np.concatenate([group_rows[g] for g in draw])
            bootd=self.d.iloc[bootix].reset_index(drop=True)
            bootX=self.X['F4'].iloc[bootix].reset_index(drop=True)
            tr=bootd.index.to_numpy()
            fac=Factory(bootd,bootX,'F4',f'bootstrap_{b}',tr)
            if route=='H-soft':
                gate=fac.fit(tr,'gate')
                calibrated=Calibrated(gate,base.models['gate'].mapping,base.models['gate'].meta)
                metal=tr[bootd.loc[tr,'gap'].to_numpy()==0];nonmetal=tr[bootd.loc[tr,'gap'].to_numpy()>0]
                m=fac.fit(metal,'metal');n=fac.fit(nonmetal,'nonmetal')
                p=calibrated.predict(full)
                v=(1-p)*(7.84+np.maximum(0,m.predict(full)))+p*np.maximum(0,n.predict(full))
            else:
                kind={'R-raw':'raw','R-log':'log','W-log':'wlog'}[route]
                tree=fac.fit(tr,kind)
                v=tree.predict(full)
                if kind!='raw':v=np.expm1(np.clip(v,-35,35))
                v=np.maximum(0,v)
            pd.DataFrame(dict(key=full.index,vhat=v)).to_csv(path,index=False)
            done.append(path.name)
            print(json.dumps(dict(bootstrap=b,fits=Budget().count())),flush=True)
        mats=np.column_stack([pd.read_csv(dest/n).set_index('key').loc[full.index,'vhat'].to_numpy() for n in done])
        pd.DataFrame(dict(key=full.index,bootstrap_sd=mats.std(axis=1,ddof=1),bootstrap_p05=np.quantile(mats,.05,axis=1),
                          bootstrap_p95=np.quantile(mats,.95,axis=1))).to_csv(dest/'dispersion.csv.gz',index=False)
        dump(dest/'manifest.json',dict(members=20,scope='P1_train02',resample_unit='directed AB',
              calibration='fixed from final full-02 fit',interpretation='conditional model dispersion; not prediction coverage',
              files={p.name:sha(p) for p in dest.glob('member_*.csv.gz')}))

    def export_predictions(self):
        final=json.loads((OUT/'final_selection.json').read_text());bundle=self.get_final_bundle(final)
        export=OUT/'predictions';export.mkdir(exist_ok=True)
        dispersion=pd.read_csv(OUT/'bootstrap/dispersion.csv.gz').set_index('key')
        # Final rules/model hashes freeze BEFORE first formal 04 prediction export.
        freeze=OUT/'prediction_freeze.json'
        if not freeze.exists():dump(freeze,dict(time=now(),selection_sha256=sha(OUT/'final_selection.json'),
             experiment_sha256=sha(OUT/'experiment_freeze.json'),feature_schema_sha256=sha(OUT/'feature_schema.json'),
             numeric=final['numeric'],screen=final['screen'],scope='P1_train02',screen_event='V<=2'))
        files={}
        for prefix in ('04','06','07','08','11','12'):
            dd=load_data(prefix);xx=self.bank['F4'].loc[dd.key]
            pp=bundle.predict(xx);r=pp[final['numeric']];s=pp[final['screen']]
            frame=dd[['id','A','B','X','key']].copy()
            frame['pool_id']=prefix;frame['model_scope']='P1_train02';frame['vhat_raw']=r['vhat_raw'];frame['vhat']=r['vhat']
            frame['clip_flag']=r['vhat_raw']<0;frame['regression_model_id']=final['numeric']
            frame['screen_score']=s['score'];frame['screen_event']='V<=2';frame['screen_model_id']=final['screen']
            for key in ('p_nonmetal','p_near_given_nonmetal'):
                frame[key]=s.get(key,r.get(key,np.full(len(dd),np.nan)))
            frame['calibration_status']='OOF_fitted; see independent reliability report' if final['screen'] not in REG else 'regression_ordering; not_probability'
            for key in ('bootstrap_sd','bootstrap_p05','bootstrap_p95'):frame[key]=dispersion.loc[dd.key,key].to_numpy()
            assert frame.vhat.notna().all() and (frame.vhat>=0).all() and frame.key.is_unique
            name=f'{prefix}_P1_train02_predictions.csv';frame.to_csv(export/name,index=False,float_format='%.17g');files[name]=sha(export/name)
            top=ordered(frame.screen_score,frame.key)[:20]
            frame.iloc[top].to_csv(export/f'{prefix}_screen_top20.csv',index=False,float_format='%.17g')
            # Independent batch/order invariance: predictions do not depend on pool composition.
            chosen=np.arange(min(5,len(dd)))
            reverse=bundle.predict(xx.iloc[chosen[::-1]])
            np.testing.assert_allclose(reverse[final['numeric']]['vhat'][::-1],r['vhat'][chosen],rtol=1e-12,atol=1e-12)
            for i in chosen:
                one=bundle.predict(xx.iloc[[i]])
                np.testing.assert_allclose(one[final['screen']]['score'],s['score'][[i]],rtol=1e-12,atol=1e-12)
        dump(export/'manifest.json',dict(time=now(),files=files,scope='P1_train02',
             P23_training='Deferred to P2/P3; these tables are not labeled P23_train02val03',
             roundtrip_float64=True,pool_order_invariance=True,no_hardware_execution=True))
        print(json.dumps(dict(exported=len(files),fits=Budget().count())),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['main','stress','final','diagnostics','export','all'])
    args=parser.parse_args();e=Experiment()
    stages=['main','stress','final','diagnostics','export'] if args.stage=='all' else [args.stage]
    for s in stages:
        getattr(e,{'final':'choose_final','export':'export_predictions'}.get(s,s))()
    print(json.dumps(dict(finished=stages,fits=Budget().count())),flush=True)


if __name__=='__main__':main()
