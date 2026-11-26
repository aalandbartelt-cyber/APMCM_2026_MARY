"""Domain-local fits, OOF calibration, content-addressed cache and exact fit ledger."""
from pathlib import Path
import hashlib
import json
import sys
import time
import numpy as np
import pandas as pd
from scipy.ndimage import convolve1d
from scipy.optimize import minimize
from scipy.special import expit, logit
from common import OUT, EPS, SEED, Budget, dump, fold_ids, stable, now

# An isolated Python package contains the original 3.3.5 wrapper and patched library.
sys.path.insert(0, str(OUT / 'lightgbm_python'))
import lightgbm as lgb

PARAMS = dict(learning_rate=.03, num_leaves=15, min_data_in_leaf=40,
              lambda_l2=1., feature_fraction=1., bagging_fraction=1., bagging_freq=0,
              verbosity=-1, num_threads=4, deterministic=True, force_col_wise=True,
              seed=SEED, feature_fraction_seed=SEED, bagging_seed=SEED, data_random_seed=SEED)


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class Tree:
    def __init__(self, meta, booster=None):
        self.meta, self.booster = meta, booster

    def predict(self, X):
        if self.meta['constant'] is not None:
            return np.full(len(X), self.meta['constant'], dtype=float)
        vals = X[self.meta['columns']].to_numpy(dtype=float)
        if self.meta['impute'] is not None:
            vals = np.where(np.isnan(vals), np.array(self.meta['impute'])[None,:], vals)
        return self.booster.predict(vals, raw_score=True, num_threads=4)

    def normalized(self, X):
        return (self.predict(X)-self.meta['score_mean'])/self.meta['score_std']


class Calibrated:
    def __init__(self, tree, mapping, meta):
        self.tree, self.mapping, self.meta = tree, mapping, meta

    def predict(self, X):
        a,b = self.mapping
        return expit(np.clip(a+b*self.tree.normalized(X),-35,35))

    def raw(self, X):
        s = self.tree.normalized(X) if self.meta['kind'].startswith('rank') else self.tree.predict(X)
        return expit(np.clip(s,-35,35))


class Factory:
    def __init__(self, data, X, feature_set, phase, allowed, evaluation=()):
        self.data, self.X, self.feature_set, self.phase = data, X, feature_set, phase
        self.allowed = set(map(int,allowed)); self.evaluation = set(map(int,evaluation))
        assert not self.allowed.intersection(self.evaluation)
        self.cache = {}; self.cal_cache = {}; self.budget = Budget()
        self.root = OUT / 'models'; self.root.mkdir(exist_ok=True)

    def fit(self, indices, kind, query_seed=0, weights=None):
        ix = np.array(sorted(map(int,indices)), dtype=int)
        assert set(ix) <= self.allowed and not set(ix) & self.evaluation
        d = self.data.loc[ix]
        g = d.gap.to_numpy() > 0
        v = d.V.to_numpy()
        if kind == 'gate': y = g.astype(float)
        elif kind in ('near','weighted_near','rank_single','rank_hash4'): y = (v <= EPS).astype(float)
        elif kind in ('log','wlog'): y = np.log1p(v)
        elif kind == 'metal': y = v-7.84
        else: y = v.copy()
        binary = kind in ('gate','near','weighted_near')
        ranking = kind.startswith('rank')
        small = kind in ('near','nonmetal')
        params = dict(PARAMS, objective='binary' if binary else 'lambdarank' if ranking else 'regression')
        if small: params.update(num_leaves=7, min_data_in_leaf=10)
        if ranking: params.update(label_gain=[0,1], lambdarank_truncation_level=23, metric='None')
        identity = dict(ids=d.id.astype(str).tolist(), features=self.feature_set, columns=list(self.X.columns),
                        target=kind, query_seed=query_seed, params=params, rounds=400,
                        weights=None if weights is None else np.asarray(weights).tolist(), schema='v2.1.0')
        key = canonical_hash(identity)
        if key in self.cache: return self.cache[key]
        path = self.root / key
        meta_path = path.with_suffix('.json'); model_path = path.with_suffix('.txt')
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            tree = Tree(meta, lgb.Booster(model_file=str(model_path)) if meta['constant'] is None else None)
            self.cache[key] = tree; return tree
        sw = None if weights is None else np.asarray(weights,dtype=float)
        if kind == 'weighted_near' and len(np.unique(y)) == 2:
            sw = np.where(y==1, len(y)/(2*sum(y)), len(y)/(2*sum(y==0)))
        if kind == 'wlog':
            bins = np.floor(y/.2).astype(int)
            frequency = np.ones(len(y)) if sw is None else sw.copy()
            counts = np.bincount(bins,weights=frequency)
            kernel = np.exp(-np.arange(-2,3,dtype=float)**2/2); kernel /= kernel.sum()
            density = np.maximum(1, convolve1d(counts.astype(float), kernel, mode='constant'))
            sw = frequency*np.minimum(10, np.sqrt(density.max()/density[bins])); sw *= frequency.sum()/sw.sum()
        constant = None
        if binary and (not len(y) or len(np.unique(y)) < 2):
            constant = float(logit((y.sum()+1)/(len(y)+2)))
        elif ranking and (not len(y) or len(np.unique(y)) < 2): constant = 0.
        elif not binary and not ranking and (len(y)<20 or d.ab.nunique()<10):
            constant = float(np.average(y,weights=sw)) if len(y) else 0.
        X = self.X.loc[ix]
        impute = None
        vals = X.to_numpy(dtype=float)
        if self.feature_set == 'F0':
            impute = X.median(axis=0).fillna(0).tolist()
            vals = np.where(np.isnan(vals), np.array(impute)[None,:], vals)
        group = None; order = np.arange(len(y))
        if ranking:
            if kind == 'rank_single': group = [len(y)]
            else:
                q = fold_ids(d.ab, 4, f'query/{query_seed}')
                order = np.argsort(q,kind='stable'); group = np.bincount(q, minlength=4)
                group = group[group>0].tolist()
            assert max(group,default=0) <= 20000
            params['label_gain'] = [0,1]
        meta = dict(key=key, target=kind, columns=list(X.columns), constant=constant, impute=impute,
                    score_mean=0., score_std=1., train_n=len(y), train_ab=d.ab.nunique(),
                    train_ids=d.id.astype(str).tolist(), feature_set=self.feature_set, query_seed=query_seed,
                    group_sizes=group, weighted_ess=None if sw is None else float(sw.sum()**2/np.square(sw).sum()))
        booster = None
        if constant is None:
            number = self.budget.reserve(phase=self.phase, target=kind, feature_set=self.feature_set,
                                         key=key, n=len(y), n_ab=d.ab.nunique(), group_sizes=group)
            start = time.monotonic()
            try:
                ds = lgb.Dataset(vals[order], label=y[order].astype(np.float32), weight=None if sw is None else sw[order].astype(np.float32),
                                 group=None if group is None else np.asarray(group,dtype=np.int32), feature_name=list(X.columns), free_raw_data=True)
                booster = lgb.train(params,ds,num_boost_round=400)
                booster.save_model(str(model_path))
                self.budget.append(dict(event='finish', fit_number=number, key=key, seconds=time.monotonic()-start))
            except Exception as exc:
                self.budget.append(dict(event='failed', fit_number=number, key=key, error=repr(exc)))
                raise
        tree = Tree(meta,booster)
        score = tree.predict(X)
        if len(score):
            meta['score_mean'] = float(score.mean()); meta['score_std'] = max(float(score.std()),1e-8)
        dump(meta_path,meta); self.cache[key]=tree
        return tree

    def calibrate(self, indices, kind):
        ix = np.array(sorted(map(int,indices)),dtype=int)
        ckey = canonical_hash(dict(indices=ix.tolist(), features=self.feature_set, kind=kind))
        if ckey in self.cal_cache: return self.cal_cache[ckey]
        d = self.data.loc[ix]
        y = (d.gap.to_numpy()>0).astype(float) if kind=='gate' else (d.V.to_numpy()<=EPS).astype(float)
        cp = OUT / 'calibration' / (ckey+'.json')
        tree = self.fit(ix,kind)
        if cp.exists():
            meta=json.loads(cp.read_text());obj=Calibrated(tree,meta['mapping'],meta);self.cal_cache[ckey]=obj;return obj
        if len(np.unique(y))<2 or d.ab.nunique()<2:
            mapping=[float(logit((y.sum()+1)/(len(y)+2))),0.]
            meta=dict(kind=kind,mapping=mapping,status='constant_prior',n=len(y),n_positive=int(y.sum()),apparent_only=True)
        else:
            folds=fold_ids(d.ab,2,'calibration/0')
            z=np.empty(len(ix)); raw=np.empty(len(ix))
            for k in range(2):
                t=self.fit(ix[folds!=k],kind)
                xe=self.X.loc[ix[folds==k]]
                z[folds==k]=t.normalized(xe)
                raw[folds==k]=expit(t.normalized(xe) if kind.startswith('rank') else t.predict(xe))
            z=np.clip(z,-100,100)
            def loss(ab):
                a,b=ab;s=a+b*z
                value=np.sum(np.logaddexp(0,s)-y*s)+.5*b*b
                err=expit(s)-y
                return value,np.array([err.sum(),np.dot(err,z)+b])
            sol=minimize(loss,[float(logit((y.sum()+1)/(len(y)+2))),1.],method='L-BFGS-B',jac=True,bounds=[(-35,35),(0,50)])
            mapping=sol.x.tolist() if sol.success and np.isfinite(sol.fun) else [float(logit((y.sum()+1)/(len(y)+2))),0.]
            cal=expit(mapping[0]+mapping[1]*z)
            meta=dict(kind=kind,mapping=mapping,status='ok' if sol.success else 'optimizer_fallback',
                      n=len(y),n_positive=int(y.sum()),apparent_only=True,
                      apparent_brier_raw=float(np.mean((raw-y)**2)),apparent_brier_cal=float(np.mean((cal-y)**2)),
                      note='Calibration fitting diagnostics; independent reliability uses inner/outer evaluation only.')
            cp.parent.mkdir(parents=True,exist_ok=True)
            pd.DataFrame(dict(id=d.id.values,fold=folds,y=y,z=z,raw_probability=raw,apparent_calibrated_probability=cal)).to_csv(cp.with_suffix('.csv.gz'),index=False)
        dump(cp,meta)
        obj=Calibrated(tree,mapping,meta);self.cal_cache[ckey]=obj;return obj


class Bundle:
    def __init__(self,factory,indices,routes):
        self.factory=factory;self.indices=np.array(indices,dtype=int);self.routes=routes;self.models={}
        d=factory.data.loc[self.indices];g=d.gap.to_numpy()>0
        if any(r in routes for r in ('H-soft','S-eps')):self.models['gate']=factory.calibrate(self.indices,'gate')
        for r in routes:
            if r in ('R-raw','R-log','W-log'):
                self.models[r]=factory.fit(self.indices,{'R-raw':'raw','R-log':'log','W-log':'wlog'}[r])
            elif r=='H-soft':
                self.models['metal']=factory.fit(self.indices[~g],'metal')
                self.models['nonmetal']=factory.fit(self.indices[g],'nonmetal')
            elif r=='S-eps':self.models['near']=factory.calibrate(self.indices[g],'near')
            elif r=='B-eps':self.models[r]=factory.calibrate(self.indices,'weighted_near')
            elif r.startswith('L-'):
                self.models[r]=factory.calibrate(self.indices,'rank_single' if r=='L-single' else 'rank_hash4')

    def predict(self,X):
        out={}
        p=self.models['gate'].predict(X) if 'gate' in self.models else None
        for r in self.routes:
            pred={}
            if r in ('R-raw','R-log','W-log'):
                raw=self.models[r].predict(X)
                if r!='R-raw':raw=np.expm1(np.clip(raw,-35,35))
                v=np.maximum(0,raw);pred=dict(vhat_raw=raw,vhat=v,score=-v)
            elif r=='H-soft':
                m=7.84+np.maximum(0,self.models['metal'].predict(X));n=np.maximum(0,self.models['nonmetal'].predict(X))
                v=(1-p)*m+p*n
                pred=dict(vhat_raw=v,vhat=v,score=-v,p_nonmetal=p,p_nonmetal_raw=self.models['gate'].raw(X),
                          vhat_hard=np.where(p>=.5,n,m),vhat_nonmetal_only=n)
            elif r=='S-eps':
                q=self.models['near'].predict(X)
                pred=dict(score=p*q,p_nonmetal=p,p_near_given_nonmetal=q,
                          p_nonmetal_raw=self.models['gate'].raw(X),p_near_raw=self.models['near'].raw(X))
            else:
                obj=self.models[r];pred=dict(score=obj.predict(X),score_raw_probability=obj.raw(X),rank_score=obj.tree.predict(X))
            for name,values in pred.items():assert np.isfinite(values).all(),(r,name)
            out[r]=pred
        return out

    def export(self):
        result={}
        for k,obj in self.models.items():
            if isinstance(obj,Calibrated):result[k]=dict(tree_key=obj.tree.meta['key'],calibration=obj.meta)
            else:result[k]=dict(tree_key=obj.meta['key'])
        return result
