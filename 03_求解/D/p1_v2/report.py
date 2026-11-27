"""Post-freeze descriptive analysis and conditional AB bootstrap; no new fitting of any kind."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from common import ROOT,OUT,CODE,ROUTES,REG,SEED,Budget,dump,sha,now
from metrics import evaluate,ordered
from hardening_tables import build_main_tables

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
        return str(x).replace('EF@','EF_{V<=2}@').replace('|', '\\|')
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


def frequency_ef(counts, gid, y, order, k=20):
    """Top-k on an exactly duplicated cluster sample, not unique-key Top-k."""
    ng = counts.shape[1]
    M = counts @ np.bincount(gid, weights=y, minlength=ng)
    N = counts @ np.bincount(gid, minlength=ng)
    prefix = order[:min(512, len(order))]
    w = counts[:, gid[prefix]]
    if np.any(w.sum(axis=1) < k):
        prefix = order
        w = counts[:, gid[prefix]]
    before = np.cumsum(w, axis=1) - w
    allocated = np.minimum(w, np.maximum(0, k - before))
    hits = allocated @ y[prefix]
    return np.divide(hits / np.minimum(k, N), M / N,
                     out=np.full(len(counts), np.nan), where=M > 0), N


def cluster_bootstrap(frames, pairs, n=5000):
    """Paired AB resampling within fixed outer folds; macro fold Top-20 EF.

    All five fold endpoints must be defined. RMSE remains a pooled row metric.
    These are conditional intervals for fixed predictions, not refit intervals.
    """
    first = next(iter(frames.values())).sort_values('key').reset_index(drop=True)
    assert first.key.is_unique
    assert 'outer_fold' in first and first.outer_fold.notna().all()
    assert first.groupby('ab').outer_fold.nunique().max() == 1, 'AB crosses outer folds'
    keys = first.key.to_numpy()
    folds = sorted(first.outer_fold.unique())
    rng = np.random.default_rng(SEED + 50000)
    strata = []
    for fold in folds:
        ix = np.flatnonzero(first.outer_fold.to_numpy() == fold)
        g = first.iloc[ix]
        groups = sorted(g.ab.unique())
        gid = g.ab.map({ab: i for i, ab in enumerate(groups)}).to_numpy()
        ng = len(groups)
        counts = rng.multinomial(ng, np.full(ng, 1/ng), size=n).astype(np.int32)
        strata.append((ix, gid, counts))
    stats, points = {}, {}
    for name, frame in frames.items():
        assert frame.key.is_unique and set(frame.key) == set(keys), name
        frame = frame.set_index('key').loc[keys].reset_index()
        for col in ('ab', 'outer_fold', 'V'):
            np.testing.assert_array_equal(frame[col], first[col], err_msg=name + ':' + col)
        ef, point_ef, sses, ns = [], [], [], []
        numeric = 'vhat' in frame and frame.vhat.notna().all()
        for ix, gid, counts in strata:
            g = frame.iloc[ix]
            y = (g.V.to_numpy() <= 2)
            order = ordered(g.score, g.key)
            one, N = frequency_ef(counts, gid, y, order)
            ef.append(one)
            point_ef.append((y[order[:20]].mean() / y.mean()) if y.any() else np.nan)
            ns.append(N)
            if numeric:
                sse = np.bincount(gid, weights=(g.vhat.to_numpy()-g.V.to_numpy())**2,
                                  minlength=counts.shape[1])
                sses.append(counts @ sse)
        # np.mean intentionally propagates any undefined fold (no nanmean).
        stats[name] = {'EF_macro@20': np.mean(ef, axis=0)}
        points[name] = {'EF_macro@20': np.mean(point_ef)}
        if numeric:
            stats[name]['RMSE'] = np.sqrt(np.sum(sses, axis=0) / np.sum(ns, axis=0))
            points[name]['RMSE'] = np.sqrt(np.mean((frame.vhat-frame.V)**2))
    records = []
    for a, b in pairs:
        for metric in sorted(set(stats[a]) & set(stats[b])):
            diff = stats[a][metric] - stats[b][metric]
            ok = np.isfinite(diff)
            q = np.quantile(diff[ok], [.025, .5, .975]) if ok.any() else [np.nan]*3
            records.append(dict(model=a, reference=b, metric=metric,
                endpoint='EF_{V<=2}@20_macro_outer_folds' if metric == 'EF_macro@20' else 'pooled_OOF_RMSE',
                n_outer_folds=len(folds), n_resamples=n, n_valid=int(ok.sum()), n_undefined=int((~ok).sum()),
                delta_point=points[a][metric]-points[b][metric],
                delta_p025=q[0], delta_median=q[1], delta_p975=q[2],
                sampling='paired AB clusters; independently resample inside each fixed outer fold',
                inference='conditional on fixed OOF and prior selection; percentile interval; no multiplicity correction'))
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
    pooled=[];raw_order_checks=[]
    assert (dest/'oof_calibration_consistency.csv').exists(), 'Original diagnostics required; no fitting allowed'
    for route,frame in frames.items():
        assert frame.key.is_unique and len(frame)==11256
        pooled.append(dict(route=route,**evaluate(frame,preds(frame))))
        if route not in REG:
            if route in ('B-eps','L-single','L-hash4'):
                for fold in ['pooled']+list(range(5)):
                    g=frame if fold=='pooled' else frame[frame.outer_fold==fold]
                    cal_top=set(g.iloc[ordered(g.score,g.key)[:20]].key)
                    raw_top=set(g.iloc[ordered(g.rank_score,g.key)[:20]].key)
                    raw_order_checks.append(dict(route=route,fold=fold,top20_overlap=len(cal_top&raw_top),
                        cal_top20_fold_counts=json.dumps(g.iloc[ordered(g.score,g.key)[:20]].outer_fold.value_counts().to_dict()),
                        note='Within-fold monotonicity and cross-fold scale diagnostic; not an extra selection rule'))
    pool=pd.DataFrame(pooled);pool['p_uniform_holm']=holm(pool['p_uniform@20']);pool.to_csv(dest/'pooled_oof_diagnostic.csv',index=False)
    pd.DataFrame(raw_order_checks).to_csv(dest/'oof_calibration_ranking_checks.csv',index=False)
    nested=json.loads((OUT/'nested_selection_results.json').read_text())
    main_table, fold_table = build_main_tables(allmetrics, nested, summary_metrics)
    fold_table.rename(columns={c:c.replace('EF@','EF_{V<=2}@') for c in fold_table.columns}).to_csv(dest/'P1_main_per_fold.csv',index=False)
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
    f3=pd.concat([pd.read_csv(OUT/'domains'/f'feature_F3_{f}.csv.gz').assign(outer_fold=f) for f in range(5)])
    compare['R-log_F3']=f3;pairs.append(('R-log','R-log_F3'))
    for feature in ('minus_electronic','minus_geometry','minus_xstats'):
        aa=pd.concat([pd.read_csv(OUT/'domains'/f'ablation_{feature}_{f}.csv.gz').assign(outer_fold=f) for f in range(5)])
        for route in set([final['numeric'],final['screen']]):
            name=route+'_'+feature;compare[name]=aa[aa.route==route];pairs.append((name,route))
    assert (dest/'paired_AB_bootstrap_pooled_diagnostic_legacy.csv').exists(), 'Preserve original pooled results before reporting'
    boot=cluster_bootstrap(compare,list(dict.fromkeys(pairs)))
    boot.to_csv(dest/'paired_AB_bootstrap_5000.csv',index=False)
    legacy=pd.read_csv(dest/'paired_AB_bootstrap_pooled_diagnostic_legacy.csv')
    legacy['metric']=legacy['metric'].replace({'EF@20':'EF_macro@20'})
    oldcols=['model','reference','metric','delta_p025','delta_median','delta_p975','n_valid']
    legacy=legacy[oldcols].rename(columns={c:'legacy_pooled_'+c for c in oldcols if c not in ('model','reference','metric')})
    comparison=boot.merge(legacy,on=['model','reference','metric'],how='left',validate='one_to_one')
    comparison['legacy_endpoint']='single pooled Top-20 EF / pooled RMSE; global AB resampling; diagnostic only'
    comparison.to_csv(dest/'paired_AB_bootstrap_endpoint_comparison.csv',index=False)
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
    # The original model card and fitted calibration diagnostics remain byte-identical.
    manifest=dict(time=now(),fits=len(attempts),failed_attempts=len(failures),hard_limit=1000,
        numeric=final['numeric'],screen=final['screen'],no_new_training_for_report=True,
        files={p.name:sha(p) for p in dest.glob('*') if p.is_file() and p.name!='manifest.json'})
    dump(dest/'manifest.json',manifest)
    write_report(main_table,v03,selected,numeric,stress,boot,manifest,final)
    print(json.dumps(dict(report_complete=True,fits=len(attempts),numeric=final['numeric'],screen=final['screen'])),flush=True)


def bootstrap_interpretation(boot):
    parts=[]
    for metric in ('RMSE','EF_macro@20'):
        r=boot[(boot.model=='H-soft') & (boot.reference=='R-log') & (boot.metric==metric)].iloc[0]
        status='区间跨零，不能声称稳定优势' if r.delta_p025<=0<=r.delta_p975 else '区间不跨零；只支持本条件评估中的差异'
        parts.append(f'H-soft − R-log 的 {metric} 差为 {r.delta_point:.4f}，95% 区间 [{r.delta_p025:.4f}, {r.delta_p975:.4f}]：{status}。')
    return ' '.join(parts)


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
    cols=['route','row_kind','RMSE','metal_MSE_contribution','nonmetal_MSE_contribution','EF@20_mean','hits20_sum','NDCG@20_mean','regret@20_mean']
    vcols=['route','row_kind','RMSE','MAE','metal_MSE_contribution','nonmetal_MSE_contribution','EF@20','hits@20','NDCG@20','regret@20']
    for c in vcols:
        if c not in val:val[c]=np.nan
    text=f'''# P1 v2.1 最终实验报告

日期：2026-11-27（P0 收尾加固）。状态：P1 实施完成；本报告只重算既有表的统计，无任何新拟合或选模。

最终数值模型：**{final['numeric']}**；最终近正例筛选模型：**{final['screen']}**。筛选事件固定为 **V<=2**，不是 V=0。正式数值输出与筛选打分分列。

## 主实验结果

下表 RMSE 和两项 MSE 贡献来自拼接的完整外层 OOF；EF/NDCG/regret 是五个完整外折评估池的均值。每折预算 20，因此 hits20_sum 的总预算为 100，不能解释为单池 Top-20 命中。

{md(table,cols)}

表中同时列出八条登记候选、三条固定基线及两条嵌套选择流程。基线不参与新增选模；加性 Ridge 为原先五折的 alpha=1 模型，均值为训练折均值，random_hash 为既定随机排序的一次实现（本次 0/100，理论期望 EF=1，不能把实现值换成期望）。逐折 N/M/h 和内层选定身份见 `P1_main_per_fold.csv`，汇总 CSV 也包含逐折向量。候选表仍有开发选择乐观性；嵌套流程另列如下：

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

概率校准在训练域 OOF 拟合。独立外层的 Brier、可靠性曲线、诊断斜率/截距以及 raw/calibrated OOF 拼接名单比较分别保存。本次复用原有诊断回归产物，不重新拟合，不据结果再选校准器。纯筛选器没有原尺度 RMSE。

拼接 OOF 的独立校准诊断如下；理想诊断截距/斜率为 0/1，但这里不据此作新的硬筛选：

{md(calibration,['route','brier','mean_probability','prevalence','calibration_intercept','calibration_slope'])}

门控平均 Brier 由 0.015913 变为 0.015893，条件事件头由 0.156119 变为 0.155870，改善很小。S-eps 乘积的诊断斜率约 1.76，说明分量经过校准并不保证乘积整体充分校准。B-eps 的 Brier 从 0.007372 降为 0.005750；不能把概率刻度改进等同于排序改进。

两种排序器及 B-eps 在每个外折内，校准前后 Top-20 都保持 20/20 一致；拼接 OOF 时重合数为 15/20 或 16/20。跨折尺度会改变全池排序，因此拼接名单作为诊断单列，没有替代每折完整池主终点。

额外 Query 种子相对登记种子 0 的稳定性：

{md(seed)}

种子 0 的 L-hash4 平均 EF 为 46.8397。额外种子 Top-20 平均重合约 15/20，不能称名单完全稳定；也没有把额外种子的较好结果替换主结果。单 Query 在本轮二元 relevance、固定容量配置下弱于四 Query，这不构成对全部 LambdaRank 设置的结论。

配对 AB bootstrap 的固定比较：在每个既定外折内分别重采样 AB，逐折各取 Top-20 后等权平均 EF，与主表一致。任一折 M=0 则该次完整宏平均无定义，不能只平均其余折。RMSE 仍按行汇总。5000 次均条件于既有 OOF 和既往选择，不包含完整研究选择不确定性；区间未作多重区间校正，按探索性解释：

{md(boot,['model','reference','metric','delta_point','delta_p025','delta_median','delta_p975','n_valid'])}

{bootstrap_interpretation(boot)}

旧全局 pooled Top-20 区间完整保留为独立诊断 `paired_AB_bootstrap_pooled_diagnostic_legacy.csv`，其 EF 只用一次 Top-20，不能与五折宏平均的区间混用。并列表 `paired_AB_bootstrap_endpoint_comparison.csv` 的 legacy_pooled_* 列只作诊断。

既有 20 个重训 bootstrap 成员的池内最优与 Top-20 稳定性（本轮不重训）：

{md(stability,['pool','nominal_minimizer_frequency','distinct_minimizers','top20_overlap_mean'])}

04 的名义最小值候选仅在 4/20 个成员中仍为最小，20 个成员出现 14 个不同最小值候选；这只是身份轮换。07/08/11/12 的完整 rank、入选频率、双向决策 regret、最优间隔、家族集中度及 split-half 结果见 `codex/P1_HARDENING_REPORT.md` 和 `artifacts/p1_v21/hardening/`。必须结合代价判定近优平台，不能仅据身份频率称为失控。

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
