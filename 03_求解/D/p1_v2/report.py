"""Post-freeze descriptive analysis and conditional AB bootstrap; never fits trees."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.special import logit, expit
from scipy.optimize import minimize
from common import ROOT,OUT,CODE,ROUTES,REG,SEED,Budget,dump,sha,now
from metrics import evaluate,ordered,probability_metrics

PRED_COLUMNS=['score','vhat','vhat_raw','p_nonmetal','p_nonmetal_raw','p_near_given_nonmetal','p_near_raw',
              'score_raw_probability','rank_score','vhat_hard','vhat_nonmetal_only']


def preds(frame):
    return {k:frame[k].to_numpy() for k in PRED_COLUMNS if k in frame and frame[k].notna().all()}


def holm(p):
    x=np.asarray(p,dtype=float);out=np.full(len(x),np.nan);valid=np.flatnonzero(np.isfinite(x));order=valid[np.argsort(x[valid])]
    if len(order):out[order]=np.minimum(1,np.maximum.accumulate(x[order]*np.arange(len(order),0,-1)))
    return out


def md(frame,columns=None,digits=4):
    df=frame[columns] if columns else frame
    df=df.rename(columns={c:c.replace('EF@','EF_{V<=2}@') for c in df.columns})
    def fmt(x):
        if x is None or (isinstance(x,(float,np.floating)) and not np.isfinite(x)):return 'NA'
        if isinstance(x,(float,np.floating)):return f'{x:.{digits}f}'
        return str(x).replace('EF@','EF_{V<=2}@')
    lines=['| '+' | '.join(df.columns)+' |','| '+' | '.join(['---']*len(df.columns))+' |']
    lines.extend('| '+' | '.join(fmt(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))
    return '\n'.join(lines)


def summary_metrics(rows,keys):
    result=[]
    for vals,g in rows.groupby(keys,dropna=False):
        if not isinstance(vals,tuple):vals=(vals,)
        r=dict(zip(keys,vals));r['evaluations']=len(g);r['screen_event']='V<=2'
        r['EF_defined_evaluations']=int(g['EF@20'].notna().sum())
        r['EF_undefined_evaluations']=int(g['EF@20'].isna().sum())
        for col in ['EF@20','NDCG@20','regret@20','hits@20','gate_brier','gate_raw_brier','conditional_brier','conditional_raw_brier','screen_brier','screen_raw_brier']:
            if col in g:r[col+'_mean']=g[col].mean()
        for col in ['metal_MSE_contribution','nonmetal_MSE_contribution','metal_MSE','nonmetal_MSE','MAE']:
            if col in g and g[col].notna().all():
                weights=g.n_metal if col=='metal_MSE' else g.n_nonmetal if col=='nonmetal_MSE' else g.N
                r[col]=np.average(g[col],weights=weights) if weights.sum() else np.nan
        if 'RMSE' in g and g.RMSE.notna().all():r['RMSE_pooled']=float(np.sqrt(np.average(g.RMSE**2,weights=g.N)))
        r['N_evaluated_sum']=int(g.N.sum());r['hits20_sum']=int(g['hits@20'].sum())
        result.append(r)
    return pd.DataFrame(result)


def diagnostic_calibration(y,p):
    """Slope/intercept fitted for diagnosis only; never changes any prediction."""
    y=np.asarray(y,float);z=logit(np.clip(np.asarray(p),1e-8,1-1e-8))
    if len(np.unique(y))<2 or np.std(z)<1e-8:return dict(calibration_intercept=np.nan,calibration_slope=np.nan)
    def loss(ab):
        a,b=ab;t=a+b*z;err=expit(t)-y
        return np.sum(np.logaddexp(0,t)-y*t)+.0001*(a*a+b*b),np.array([err.sum()+.0002*a,np.dot(err,z)+.0002*b])
    fit=minimize(loss,[0.,1.],jac=True,method='L-BFGS-B',bounds=[(-50,50),(-20,20)])
    return dict(calibration_intercept=fit.x[0],calibration_slope=fit.x[1],diagnostic_only=True)


def cluster_bootstrap(frames,pairs,n=5000):
    """Frequency representation exactly duplicates AB clusters, including top-k rows."""
    first=next(iter(frames.values())).sort_values('key')
    keys=first.key.to_numpy();groups=sorted(first.ab.unique());lookup={g:i for i,g in enumerate(groups)}
    gid=first.ab.map(lookup).to_numpy();ng=len(groups)
    y=(first.V.to_numpy()<=2);v=first.V.to_numpy();rng=np.random.default_rng(SEED+50000)
    counts=rng.multinomial(ng,np.full(ng,1/ng),size=n).astype(np.int32)
    near_by_group=np.bincount(gid,weights=y,minlength=ng)
    rows_by_group=np.bincount(gid,minlength=ng)
    M=counts@near_by_group;N=counts@rows_by_group
    stats={};records=[]
    for name,frame in frames.items():
        frame=frame.set_index('key').loc[keys].reset_index()
        order=ordered(frame.score,keys)
        # Only the leading 512 ranks are normally needed; the fallback is exact.
        prefix=order[:min(512,len(order))];w=counts[:,gid[prefix]]
        if np.any(w.sum(axis=1)<20):prefix=order;w=counts[:,gid[prefix]]
        before=np.cumsum(w,axis=1)-w
        allocated=np.minimum(w,np.maximum(0,20-before))
        hits=allocated@y[prefix]
        ef=np.divide(hits/20,M/N,out=np.full(n,np.nan),where=M>0)
        result={'EF@20':ef}
        if 'vhat' in frame and frame.vhat.notna().all():
            sse_by_group=np.bincount(gid,weights=(frame.vhat.to_numpy()-v)**2,minlength=ng)
            result['RMSE']=np.sqrt((counts@sse_by_group)/N)
        stats[name]=result
    for a,b in pairs:
        for metric in set(stats[a])&set(stats[b]):
            diff=stats[a][metric]-stats[b][metric];ok=np.isfinite(diff)
            q=np.quantile(diff[ok],[.025,.5,.975]) if ok.any() else [np.nan]*3
            records.append(dict(model=a,reference=b,metric=metric,n_resamples=n,n_valid=int(ok.sum()),
                                delta_p025=q[0],delta_median=q[1],delta_p975=q[2],
                                inference='conditional on fixed OOF and prior model selection; AB-cluster percentile interval'))
    return pd.DataFrame(records)


def main():
    dest=OUT/'results';dest.mkdir(exist_ok=True)
    final=json.loads((OUT/'final_selection.json').read_text())
    rows=[]
    for path in sorted((OUT/'domains').glob('*.json')):
        rows.extend(json.loads(path.read_text()).get('metrics',[]))
    allmetrics=pd.DataFrame(rows)
    allmetrics['screen_event']='V<=2'
    allmetrics['primary_screen_metric']='EF_{V<=2}@20'
    outer=allmetrics[allmetrics.protocol=='outer'].copy()
    outer['p_uniform_holm']=holm(outer['p_uniform@20'])
    allmetrics.to_csv(dest/'all_domain_metrics.csv',index=False)
    outer.to_csv(dest/'outer_candidate_metrics.csv',index=False)
    sums=summary_metrics(outer,['route','feature_set']);sums.to_csv(dest/'outer_summary.csv',index=False)
    stress=allmetrics[allmetrics.protocol.isin(['element','xleave','target'])]
    summary_metrics(stress,['protocol','route']).to_csv(dest/'stress_summary.csv',index=False)
    stress.to_csv(dest/'stress_detail.csv',index=False)
    summary_metrics(allmetrics[allmetrics.protocol.isin(['feature','ablation','repeat','baseline'])],['protocol','route','feature_set']).to_csv(dest/'diagnostic_summary.csv',index=False)
    allmetrics[allmetrics.protocol=='query_seed'].to_csv(dest/'query_seed_stability.csv',index=False)
    oof=pd.concat([pd.read_csv(OUT/'domains'/f'main_outer_{f}.csv.gz').assign(outer_fold=f) for f in range(5)],ignore_index=True)
    oof.to_csv(dest/'outer_oof_predictions.csv.gz',index=False)
    frames={r:g.sort_values('key').reset_index(drop=True) for r,g in oof.groupby('route')}
    pooled=[];cal=[];raw_order_checks=[]
    for route,frame in frames.items():
        assert frame.key.is_unique and len(frame)==11256
        pooled.append(dict(route=route,**evaluate(frame,preds(frame))))
        if route not in REG:
            for fold in ['pooled']+list(range(5)):
                g=frame if fold=='pooled' else frame[frame.outer_fold==fold]
                cal.append(dict(route=route,fold=fold,**probability_metrics(g.V<=2,g.score),**diagnostic_calibration(g.V<=2,g.score)))
            if route in ('B-eps','L-single','L-hash4'):
                for fold in ['pooled']+list(range(5)):
                    g=frame if fold=='pooled' else frame[frame.outer_fold==fold]
                    cal_top=set(g.iloc[ordered(g.score,g.key)[:20]].key)
                    raw_top=set(g.iloc[ordered(g.rank_score,g.key)[:20]].key)
                    raw_order_checks.append(dict(route=route,fold=fold,top20_overlap=len(cal_top&raw_top),
                        cal_top20_fold_counts=json.dumps(g.iloc[ordered(g.score,g.key)[:20]].outer_fold.value_counts().to_dict()),
                        note='Within-fold monotonicity and cross-fold scale diagnostic; not an extra selection rule'))
    pool=pd.DataFrame(pooled);pool['p_uniform_holm']=holm(pool['p_uniform@20']);pool.to_csv(dest/'pooled_oof_diagnostic.csv',index=False)
    pd.DataFrame(cal).to_csv(dest/'oof_calibration_consistency.csv',index=False)
    pd.DataFrame(raw_order_checks).to_csv(dest/'oof_calibration_ranking_checks.csv',index=False)
    # Correct conditional MSE values for pooled rows are taken from the OOF table.
    exact=pool[['route','metal_MSE','nonmetal_MSE','metal_MSE_contribution','nonmetal_MSE_contribution','RMSE','MAE']]
    main_table=sums[['route','feature_set','evaluations','EF@20_mean','hits20_sum','NDCG@20_mean','regret@20_mean']].merge(exact,on='route')
    public_table=main_table.rename(columns={'EF@20_mean':'EF_{V<=2}@20_mean'}).assign(screen_event='V<=2')
    public_table.to_csv(dest/'P1_final_experiment_table.csv',index=False)
    public_table.to_csv(ROOT/'codex/P1_FINAL_RESULTS_v2.1.csv',index=False)
    v03=pd.DataFrame(json.loads((OUT/'03_results.json').read_text()));v03['p_uniform_holm']=holm(v03['p_uniform@20'])
    v03_public=v03.rename(columns={c:c.replace('EF@','EF_{V<=2}@') for c in v03.columns}).assign(screen_event='V<=2')
    v03_public.to_csv(dest/'03_development_results.csv',index=False)
    nested=json.loads((OUT/'nested_selection_results.json').read_text())
    selected=[]
    for mode in ('numeric','screen'):
        rr=[r[mode+'_result'] for r in nested]
        for x in rr:x=dict(x)
        one=summary_metrics(pd.DataFrame(rr),['protocol']).iloc[0].to_dict()
        one.update(procedure=mode,selected_per_fold=[r[mode] for r in nested]);selected.append(one)
    dump(dest/'nested_procedure_summary.json',selected)
    # Pareto only applies to routes that actually emit original-scale V.
    numeric=main_table[main_table.route.isin(REG)].copy();front=[]
    for _,r in numeric.iterrows():
        dominated=((numeric.RMSE<=r.RMSE)&(numeric['EF@20_mean']>=r['EF@20_mean'])&
                   ((numeric.RMSE<r.RMSE)|(numeric['EF@20_mean']>r['EF@20_mean']))).any()
        front.append(not dominated)
    numeric['pareto_nondominated']=front;numeric.to_csv(dest/'regression_pareto.csv',index=False)
    # Fixed comparisons; never feed these intervals back into selection.
    compare={k:v for k,v in frames.items()}
    pairs=[(final['numeric'],'R-log'),(final['screen'],'R-log'),('S-eps','B-eps'),('L-single','L-hash4')]
    f3=pd.concat([pd.read_csv(OUT/'domains'/f'feature_F3_{f}.csv.gz') for f in range(5)])
    compare['R-log_F3']=f3;pairs.append(('R-log','R-log_F3'))
    for feature in ('minus_electronic','minus_geometry','minus_xstats'):
        aa=pd.concat([pd.read_csv(OUT/'domains'/f'ablation_{feature}_{f}.csv.gz') for f in range(5)])
        for route in set([final['numeric'],final['screen']]):
            name=route+'_'+feature;compare[name]=aa[aa.route==route];pairs.append((name,route))
    boot=cluster_bootstrap(compare,list(dict.fromkeys(pairs)))
    boot.to_csv(dest/'paired_AB_bootstrap_5000.csv',index=False)
    # Bootstrap optimizer/top-k stability on each explicit candidate pool.
    stability=[]
    for prefix in ('04','07','08','11','12'):
        p=pd.read_csv(OUT/'predictions'/f'{prefix}_P1_train02_predictions.csv').set_index('key')
        nominal=set(p.iloc[ordered(-p.vhat,p.index)[:20]].index);opt=p.iloc[ordered(-p.vhat,p.index)[0]].name
        winners=[];overlap=[]
        for b in range(20):
            member=pd.read_csv(OUT/'bootstrap'/f'member_{b:02d}.csv.gz').set_index('key').loc[p.index]
            idx=ordered(-member.vhat,member.index);winners.append(member.index[idx[0]])
            overlap.append(len(nominal&set(member.index[idx[:20]])))
        stability.append(dict(pool=prefix,n_members=20,nominal_minimizer=opt,
            nominal_minimizer_frequency=winners.count(opt)/20,distinct_minimizers=len(set(winners)),
            top20_overlap_mean=np.mean(overlap),top20_overlap_min=min(overlap),interpretation='conditional model dispersion; no truth labels'))
    pd.DataFrame(stability).to_csv(dest/'bootstrap_pool_stability.csv',index=False)
    # OOF residual scales distinguish model dispersion from predictive error.
    numframe=frames[final['numeric']]
    residual=[]
    for x,g in numframe.groupby('X'):
        e=g.vhat-g.V;residual.append(dict(X=x,n=len(g),bias=e.mean(),RMSE=np.sqrt(np.mean(e**2)),MAE=np.abs(e).mean(),q95_absolute=np.quantile(np.abs(e),.95)))
    pd.DataFrame(residual).to_csv(dest/'OOF_residual_scales_by_X.csv',index=False)
    ledger=Budget().entries();attempts=[r for r in ledger if r['event']=='start'];failures=[r for r in ledger if r['event']=='failed']
    budget=pd.DataFrame(attempts).groupby('phase',dropna=False).size().rename('attempts').reset_index();budget.to_csv(dest/'fit_counts_by_phase.csv',index=False)
    model_card=dict(version='P1 v2.1',training_scope='P1_train02',training_rows=11256,
        regression_model=final['numeric'],screen_model=final['screen'],screen_event='V<=2',
        screen_score_kind='negative_Vhat' if final['screen'] in REG else 'estimated_near_event_probability',
        inputs=['A','B','X'],feature_set='F3+E1',feature_count=336,DFT_features_used=False,
        calibration='AB-group cross-fitted sigmoid inside each training domain; independent diagnostics saved',
        validation_role='03 is development selection with historical exposure; 04 has no labels',
        uncertainty='20 AB-resampled numerical models, fixed final calibrator; no coverage guarantee',
        limitations=['No V=0 positives in development','No claim of hidden-zero recall','Final H-soft not directly covered by R-log/S-eps domain-pressure comparisons',
                     'Historical blind state cannot be restored','P23 02+03 refit deferred'],
        source_manifest_sha256=sha(OUT/'sources/source_manifest.json'),
        weights_manifest_sha256=sha(OUT/'weights_freeze_pre04.json'),
        scalar_calibrators=len(list((OUT/'calibration').glob('*.json'))),ridge_baseline_fits=5,
        fit_attempts=len(attempts),failed_attempts=len(failures))
    dump(OUT/'model_card.json',model_card)
    manifest=dict(time=now(),fits=len(attempts),failed_attempts=len(failures),hard_limit=1000,
        numeric=final['numeric'],screen=final['screen'],no_new_training_for_report=True,
        files={p.name:sha(p) for p in dest.glob('*') if p.is_file()})
    dump(dest/'manifest.json',manifest)
    write_report(main_table,v03,selected,numeric,stress,boot,manifest,final)
    print(json.dumps(dict(report_complete=True,fits=len(attempts),numeric=final['numeric'],screen=final['screen'])),flush=True)


def write_report(table,val,nested,pareto,stress,boot,manifest,final):
    report=ROOT/'codex/P1_RESULTS_v2.1.md'
    results=OUT/'results'
    diag=pd.read_csv(results/'diagnostic_summary.csv')
    feature=diag[diag.protocol.isin(['feature','ablation'])][['protocol','route','feature_set','RMSE_pooled','EF@20_mean','hits20_sum']]
    pressure=pd.read_csv(results/'stress_summary.csv')
    calibration=pd.read_csv(results/'oof_calibration_consistency.csv')
    calibration=calibration[calibration.fold=='pooled']
    seed=pd.read_csv(results/'query_seed_stability.csv').groupby('route',as_index=False).agg(
        EF_mean=('EF@20','mean'),overlap_mean=('top20_overlap','mean'),overlap_min=('top20_overlap','min'),overlap_max=('top20_overlap','max'))
    stability=pd.read_csv(results/'bootstrap_pool_stability.csv',dtype={'pool':str})
    front=', '.join(pareto.loc[pareto.pareto_nondominated,'route'])
    cols=['route','RMSE','metal_MSE_contribution','nonmetal_MSE_contribution','EF@20_mean','hits20_sum','NDCG@20_mean','regret@20_mean']
    vcols=['route','RMSE','MAE','metal_MSE_contribution','nonmetal_MSE_contribution','EF@20','hits@20','NDCG@20','regret@20']
    for c in vcols:
        if c not in val:val[c]=np.nan
    text=f'''# P1 v2.1 最终实验报告

日期：2026-11-26。状态：P1 实施完成；本报告由冻结实验产物生成，未作新一轮选模。

最终数值模型：**{final['numeric']}**；最终近正例筛选模型：**{final['screen']}**。筛选事件固定为 **V<=2**，不是 V=0。正式数值输出与筛选打分分列。

## 主实验结果

下表 RMSE 和两项 MSE 贡献来自拼接的完整外层 OOF；EF/NDCG/regret 是五个完整外折评估池的均值。每折预算 20，因此 hits20_sum 的总预算为 100，不能解释为单池 Top-20 命中。

{md(table,cols)}

这是各登记候选的配对表现；据此挑最佳再报告同一表仍有开发选择乐观性。另存嵌套流程的独立外层评价：

{md(pd.DataFrame(nested),['procedure','RMSE_pooled','EF@20_mean','hits20_sum'])}

## 03 开发选择

最多三个候选在拟合和名单冻结后一次性评估；03 不参与训练或校准，但本轮及历史均用于开发，不能称独立最终测试。此池 N=3969、M=41、k=20。

{md(val,vcols)}

固定规则分别决定数值和筛选用途。H-soft 与 B-eps 的近正例命中同为 13/20；H-soft 由预登记的 NDCG 并列规则胜出，不是 EF 更高。没有 1.02 倍 RMSE 否决门槛，没有用 03 早停或挑哈希种子。H-soft 的筛选分数仍是 -Vhat，不宣称为近正例概率。

当前四条回归候选的 Pareto 非支配集合为：**{front}**。这只限于登记菜单，不代表所有可能模型的最优性。

## 消融、外推与校准

完整逐折/逐 X/压力测试、F0/F3/F3+E1、三组反向消融、两次重复划分以及三 Query 种子记录位于 `artifacts/p1_v21/results/`。元素测试有重复覆盖的组成；X 留出同时排除测试 AB；目标区域留出不等价于真正零点外推。

特征与反向消融表：

{md(feature)}

R-log 的 F3+E1 RMSE 为 4.9048，相比 F3 的 4.9547 有小幅改善；其配对区间见下表。H-soft 去几何后的 RMSE 增加约 0.1396；去电子或去 X 统计的误差增量更小，区间跨零，不能给出独立确定贡献的强结论。两次额外分组重复合并 RMSE 为 4.6088；不同划分的 EF 仍有波动。

预登记压力测试表：

{md(pressure,['protocol','route','evaluations','EF_defined_evaluations','RMSE_pooled','EF@20_mean','hits20_sum'])}

压力测试按计划只训练 R-log 和 S-eps，**不是最终 H-soft 的直接域外验证**。EF 均值只包含 M>0 的有效评估池，其数量单列；M=0 不填零。不同协议的评估池、M 和总预算不同，不能横向按 EF 大小比较“哪种外推更容易”。V<2 区域全部留出时，S-eps 条件事件头缺正类而退化为平滑先验，该情景的排序主要依赖门控，不能解释成恢复了未见零点监督。

概率校准在训练域 OOF 拟合。独立外层的 Brier、可靠性曲线、诊断斜率/截距以及 raw/calibrated OOF 拼接名单比较分别保存。诊断回归不改变任何预测，不据结果再选校准器。纯筛选器没有原尺度 RMSE。

拼接 OOF 的独立校准诊断如下；理想诊断截距/斜率为 0/1，但这里不据此作新的硬筛选：

{md(calibration,['route','brier','mean_probability','prevalence','calibration_intercept','calibration_slope'])}

门控平均 Brier 由 0.015913 变为 0.015893，条件事件头由 0.156119 变为 0.155870，改善很小。S-eps 乘积的诊断斜率约 1.76，说明分量经过校准并不保证乘积整体充分校准。B-eps 的 Brier 从 0.007372 降为 0.005750；不能把概率刻度改进等同于排序改进。

两种排序器及 B-eps 在每个外折内，校准前后 Top-20 都保持 20/20 一致；拼接 OOF 时重合数为 15/20 或 16/20。跨折尺度会改变全池排序，因此拼接名单作为诊断单列，没有替代每折完整池主终点。

额外 Query 种子相对登记种子 0 的稳定性：

{md(seed)}

种子 0 的 L-hash4 平均 EF 为 46.8397。额外种子 Top-20 平均重合约 15/20，不能称名单完全稳定；也没有把额外种子的较好结果替换主结果。单 Query 在本轮二元 relevance、固定容量配置下弱于四 Query，这不构成对全部 LambdaRank 设置的结论。

配对 AB bootstrap 的固定比较（5000 次，条件于既有 OOF 和既往选择，不包含完整研究选择不确定性；区间未作多重区间校正，按探索性解释）：

{md(boot,['model','reference','metric','delta_p025','delta_median','delta_p975'])}

H-soft 相对 R-log 的 RMSE 差区间完全低于零，但 EF 差区间跨零。因此可报告数值误差改善证据，不能把筛选优势写成已稳定证实。

20 次重训 bootstrap 的池内最优与 Top-20 稳定性：

{md(stability,['pool','nominal_minimizer_frequency','distinct_minimizers','top20_overlap_mean'])}

04 的名义最小值候选仅在 4/20 个成员中仍为最小，20 个成员出现 14 个不同最小值候选。这反映候选最优身份不稳定，不是真实材料成功概率。

## 预算、复现与限制

- 树模型拟合尝试 **{manifest['fits']}** 次，其中失败尝试 **{manifest['failed_attempts']}** 次；硬上限 1000。失败记账，没有扩大模型菜单。
- 现有 Python/LightGBM 安装未升级；使用隔离的 3.3.5 Query 上限补丁，小规模结果逐值一致。
- 20 个 AB bootstrap 数值模型保留整表；校准器固定。输出的 sd/p05/p95 是条件模型分散度，不是保证覆盖的真实 V 区间。
- 公开文件哈希、冻结代码/划分/候选/名单哈希及完整拟合账本均保留。
- 04 共 3703 行，只有组成输入，未取得隐藏标签；不能报告真实 V=0 的命中、召回或显著性。
- 历史宿主知情风险仍存在；新冻结不恢复旧盲态。未逆推宿主、未载入外部同源材料标签。
- P2/P3 候选表全部明确标 `P1_train02`，后续 `P23_train02val03` 重训未执行。未求解 QUBO、未调用真机、未改正式论文。

## 交付索引

- 方案：`codex/P1_PLANv2.md`；代码与复现入口：`03_求解/D/p1_v2/README.md`。
- 主结果：`artifacts/p1_v21/results/P1_final_experiment_table.csv`、`03_development_results.csv`。
- 04 预测：`artifacts/p1_v21/predictions/04_P1_train02_predictions.csv`；相应 Top-20 为 `04_screen_top20.csv`。
- 完整证据：`experiment_freeze.json`、`splits.json`、`fit_ledger.jsonl`、`final_selection.json`、`prediction_freeze.json`、`results/manifest.json`。

上述近正例结果只能支持指定开发协议中的代理富集；不能直接推出隐藏零点发现、真实物理最优或可合成性。
'''
    report.write_text(text)


if __name__=='__main__':main()
