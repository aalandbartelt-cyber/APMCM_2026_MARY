"""Pool-explicit metrics; no hidden labels or inferred positives."""
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import hypergeom, kendalltau
from scipy.optimize import minimize
from sklearn.metrics import average_precision_score, log_loss
from common import EPS, stable


def ordered(scores, keys):
    ties=np.array([stable(k,'tie') for k in keys])
    return np.lexsort((ties,-np.asarray(scores)))


def probability_metrics(y,p,prefix=''):
    y=np.asarray(y);p=np.clip(np.asarray(p),1e-12,1-1e-12)
    if len(y)==0:return {prefix+'n':0}
    out={prefix+'n':len(y),prefix+'n_positive':int(y.sum()),prefix+'brier':float(np.mean((p-y)**2)),
         prefix+'log_loss':float(log_loss(y,p,labels=[0,1])),
         prefix+'pr_auc':float(average_precision_score(y,p)) if len(np.unique(y))==2 else np.nan,
         prefix+'mean_probability':float(p.mean()),prefix+'prevalence':float(y.mean())}
    bins=np.array_split(np.argsort(p,kind='stable'),min(10,len(y)))
    out[prefix+'ece']=float(sum(len(i)*abs(p[i].mean()-y[i].mean()) for i in bins)/len(y))
    return out


def reliability_rows(d,pred,route,protocol,fold):
    entries=[];y=(d.V.to_numpy()<=EPS);g=d.gap.to_numpy()>0
    checks=[]
    if route in ('S-eps','B-eps','L-single','L-hash4'):checks.append(('screen',y,pred['score'],np.ones(len(d),bool)))
    if 'p_nonmetal' in pred:checks.append(('gate',g,pred['p_nonmetal'],np.ones(len(d),bool)))
    if 'p_near_given_nonmetal' in pred:checks.append(('conditional_near',y,pred['p_near_given_nonmetal'],g))
    for head,truth,p,mask in checks:
        for group in ['ALL']+sorted(d.X.unique().tolist()):
            use=mask if group=='ALL' else mask & (d.X.to_numpy()==group)
            yy=truth[use];pp=np.asarray(p)[use]
            for b,ix in enumerate(np.array_split(np.argsort(pp,kind='stable'),min(10,len(pp))) if len(pp) else []):
                entries.append(dict(protocol=protocol,fold=fold,route=route,head=head,X=group,bin=b,n=len(ix),
                                    mean_probability=float(pp[ix].mean()),observed=float(yy[ix].mean())))
    return entries


def evaluate(d,pred,score_probability=True):
    v=d.V.to_numpy(dtype=float);g=d.gap.to_numpy()>0;y=v<=EPS
    order=ordered(pred['score'],d.key.to_numpy());N=len(d);M=int(y.sum())
    out=dict(N=N,M=M,n_ab=d.ab.nunique(),n_metal=int((~g).sum()),n_nonmetal=int(g.sum()))
    utility=np.exp(-v/2)
    for k0 in [1,5,10,20,50,100]:
        k=min(k0,N);sel=order[:k];h=int(y[sel].sum());disc=1/np.log2(np.arange(k)+2)
        idcg=float(np.sum(np.sort(utility)[::-1][:k]*disc))
        out.update({f'hits@{k0}':h,f'precision@{k0}':h/k,
            f'recall@{k0}':h/M if M else np.nan,f'EF@{k0}':(h/k)/(M/N) if M else np.nan,
            f'NDCG@{k0}':float(np.sum(utility[sel]*disc)/idcg) if idcg>0 else np.nan,
            f'regret@{k0}':float(v[sel].min()-v.min()),f'min_V@{k0}':float(v[sel].min()),
            f'mean_V@{k0}':float(v[sel].mean()),f'median_V@{k0}':float(np.median(v[sel])),
            f'n_AB@{k0}':d.iloc[sel].ab.nunique()})
    out['p_uniform@20']=float(hypergeom.sf(out['hits@20']-1,N,M,min(20,N))) if M else np.nan
    if 'vhat' in pred:
        e=np.asarray(pred['vhat'])-v;sq=e*e
        out.update(RMSE=float(np.sqrt(sq.mean())),MAE=float(np.abs(e).mean()),
            metal_MSE=float(sq[~g].mean()) if (~g).any() else np.nan,
            nonmetal_MSE=float(sq[g].mean()) if g.any() else np.nan,
            metal_MSE_contribution=float(sq[~g].sum()/N),nonmetal_MSE_contribution=float(sq[g].sum()/N),
            tail_MAE=float(np.abs(e[y]).mean()) if M else np.nan,tail_bias=float(e[y].mean()) if M else np.nan,
            tail_tau=float(kendalltau(v[y],np.asarray(pred['vhat'])[y]).statistic) if M>2 else np.nan,
            clip_fraction=float(np.mean(np.asarray(pred['vhat_raw'])<0)))
        assert np.isclose(out['RMSE']**2,out['metal_MSE_contribution']+out['nonmetal_MSE_contribution'])
    if 'p_nonmetal' in pred:
        out.update(probability_metrics(g,pred['p_nonmetal'],'gate_'))
        out.update(probability_metrics(g,pred['p_nonmetal_raw'],'gate_raw_'))
    if 'p_near_given_nonmetal' in pred:
        out.update(probability_metrics(y[g],np.asarray(pred['p_near_given_nonmetal'])[g],'conditional_'))
        out.update(probability_metrics(y[g],np.asarray(pred['p_near_raw'])[g],'conditional_raw_'))
    if 'vhat' not in pred and score_probability:out.update(probability_metrics(y,pred['score'],'screen_'))
    if 'score_raw_probability' in pred:out.update(probability_metrics(y,pred['score_raw_probability'],'screen_raw_'))
    return out


def select(metric_rows,mode):
    df=pd.DataFrame(metric_rows)
    candidates=[]
    for route,grp in df.groupby('route'):
        if mode=='regression' and (route not in ('R-raw','R-log','W-log','H-soft')):continue
        rmse=float(np.sqrt(np.average(np.square(grp.RMSE),weights=grp.N))) if 'RMSE' in grp and grp.RMSE.notna().all() else np.inf
        mae=float(np.average(grp.MAE,weights=grp.N)) if 'MAE' in grp and grp.MAE.notna().all() else np.inf
        ef=float(grp['EF@20'].mean());ndcg=float(grp['NDCG@20'].mean());regret=float(grp['regret@20'].mean())
        from common import COMPLEXITY
        tie=(rmse,mae,COMPLEXITY[route],route) if mode=='regression' else (-ef,-ndcg,regret,COMPLEXITY[route],route)
        candidates.append((tie,route))
    return min(candidates)[1]
