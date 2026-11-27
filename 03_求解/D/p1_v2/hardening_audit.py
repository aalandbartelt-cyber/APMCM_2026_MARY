"""Independently verify the zero-fit hardening deliverables and frozen inputs."""
import hashlib
import json
import numpy as np
import pandas as pd
from common import ROOT, OUT, CODE, SEED, Budget, sha, dump, now

HARD = OUT/'hardening'


def read(name):
    return json.loads((HARD/name).read_text())


def ordered_independent(values, keys):
    ties = [hashlib.sha256(('P1v2.1/tie/'+str(key)).encode()).hexdigest() for key in keys]
    return np.lexsort((ties, values))


def check_protection():
    before = read('protected_before.json')
    for path, digest in before['files'].items():
        assert sha(ROOT/path) == digest, 'Protected file changed: '+path
    for directory in ('models','calibration','domains','features','bootstrap','predictions','interface'):
        prefix = str((OUT/directory).relative_to(ROOT))+'/'
        expected = {p for p in before['files'] if p.startswith(prefix)}
        observed = {str(p.relative_to(ROOT)) for p in (OUT/directory).rglob('*') if p.is_file()}
        assert expected == observed, ('File inventory changed', directory)
    assert Budget().count() == before['fit_count'] == 914
    freeze = json.loads((OUT/'experiment_freeze.json').read_text())
    for name, digest in freeze['core_code_hashes'].items():
        assert sha(CODE/name) == digest
    original = ROOT/'codex/P1_PLANv2.1_FROZEN.md'
    assert sha(original) == freeze['plan_sha256']
    amended = ROOT/'codex/P1_PLANv2.md'
    assert amended.read_text().startswith(original.read_text().rstrip())
    receipt = read('plan_amendment_freeze.json')
    for path, field in [(amended,'amended_plan_sha256'), (HARD/'protocol.json','protocol_sha256'),
                        (HARD/'P23_construction_decision.json','decision_sha256'),
                        (HARD/'split_half_summary.csv','split_half_summary_sha256')]:
        assert sha(path) == receipt[field]
    protocol = read('protocol.json')
    assert sha(HARD/'protected_before.json') == protocol['protected_snapshot_sha256']
    legacy = ROOT/protocol['legacy_pooled_file']
    assert sha(legacy) == protocol['legacy_pooled_sha256']
    assert sha(legacy) == sha(HARD/'archive/artifacts/p1_v21/results/paired_AB_bootstrap_5000.csv')
    assert not receipt['P23_executed']
    return len(before['files'])


def check_main_table():
    main = pd.read_csv(OUT/'results/P1_final_experiment_table.csv').set_index('route')
    detail = pd.read_csv(OUT/'results/P1_main_per_fold.csv')
    assert len(main) == 13 and len(detail) == 65
    assert sha(OUT/'results/P1_final_experiment_table.csv') == sha(ROOT/'codex/P1_FINAL_RESULTS_v2.1.csv')
    nested = json.loads((OUT/'nested_selection_results.json').read_text())
    for fold in range(5):
        originals = {}
        for stem in ('main_outer','baseline'):
            records = json.loads((OUT/'domains'/f'{stem}_{fold}.json').read_text())['metrics']
            originals.update({r['route']:r for r in records if r['protocol'] in ('outer','baseline')})
        originals.update({'nested_'+mode:nested[fold][mode+'_result'] for mode in ('numeric','screen')})
        for row in detail[detail.fold == fold].itertuples():
            src = originals[row.route]
            assert row.N == src['N'] and row.M == src['M'] and row.h == src['hits@20'] and row.k == 20
            assert row.selected_numeric_route == nested[fold]['numeric']
            assert row.selected_screen_route == nested[fold]['screen']
            assert row.selection_identity == (nested[fold][row.route[7:]] if row.route.startswith('nested_') else row.route)
    for route, g in detail.groupby('route'):
        row = main.loc[route]
        expected = ((g.h/20)/(g.M/g.N)).mean()
        np.testing.assert_allclose(row['EF_{V<=2}@20_mean'], expected, atol=1e-12)
        assert row.hits20_sum == g.h.sum() and row.total_screen_budget == 100
        for col in ['N','M','h']:
            assert json.loads(row[col+'_per_fold']) == g.sort_values('fold')[col].tolist()
        if g.RMSE.notna().all():
            np.testing.assert_allclose(row.RMSE**2, np.average(g.RMSE**2, weights=g.N))
            np.testing.assert_allclose(row.RMSE**2, row.metal_MSE_contribution+row.nonmetal_MSE_contribution)
    # Registered candidate point estimates and all choices remain unchanged.
    old = pd.read_csv(HARD/'archive/codex/P1_FINAL_RESULTS_v2.1.csv').set_index('route')
    for route, row in old.iterrows():
        for col in ['RMSE','metal_MSE_contribution','nonmetal_MSE_contribution','EF_{V<=2}@20_mean','hits20_sum']:
            np.testing.assert_allclose(main.loc[route,col], row[col], atol=1e-12, equal_nan=True)
    return main


def check_bootstrap(main):
    """Literal row duplication, independent of report.frequency_ef implementation."""
    tables = [pd.read_csv(OUT/'domains'/f'main_outer_{f}.csv.gz', float_precision='round_trip').assign(fold=f)
              for f in range(5)]
    raw = pd.concat(tables)
    first = raw[raw.route=='H-soft'].sort_values('key')
    rng = np.random.default_rng(SEED+50000)
    ef = {r:[] for r in ('H-soft','R-log')}
    sse = {r:np.zeros(5000) for r in ef}; total_N = np.zeros(5000)
    for fold in range(5):
        base = first[first.fold==fold]
        groups = sorted(base.ab.unique())
        codes = base.ab.map({ab:i for i,ab in enumerate(groups)}).to_numpy()
        counts = rng.multinomial(len(groups), np.full(len(groups),1/len(groups)),size=5000)
        row_weights = counts[:, codes]
        truth = base.V.to_numpy() <= 2
        N = row_weights.sum(axis=1); M = row_weights @ truth
        total_N += N
        for route in ef:
            frame = raw[(raw.route==route)&(raw.fold==fold)].set_index('key').loc[base.key]
            order = ordered_independent(-frame.score.to_numpy(), base.key)
            hits = np.zeros(5000)
            for b in range(5000):
                duplicated = np.repeat(order, row_weights[b, order])
                hits[b] = truth[duplicated[:20]].sum()
            ef[route].append(np.divide(hits*N, 20*M, out=np.full(5000,np.nan), where=M>0))
            sse[route] += row_weights @ (frame.vhat.to_numpy()-base.V.to_numpy())**2
    differences = {'EF_macro@20': np.mean(ef['H-soft'],axis=0)-np.mean(ef['R-log'],axis=0),
                   'RMSE': np.sqrt(sse['H-soft']/total_N)-np.sqrt(sse['R-log']/total_N)}
    result = pd.read_csv(OUT/'results/paired_AB_bootstrap_5000.csv')
    for metric, diff in differences.items():
        row = result[(result.model=='H-soft')&(result.reference=='R-log')&(result.metric==metric)].iloc[0]
        np.testing.assert_allclose([row.delta_p025,row.delta_median,row.delta_p975],np.nanquantile(diff,[.025,.5,.975]),atol=1e-12)
        col = 'EF_{V<=2}@20_mean' if metric=='EF_macro@20' else 'RMSE'
        np.testing.assert_allclose(row.delta_point,main.loc['H-soft',col]-main.loc['R-log',col],atol=1e-12)
    assert (result.n_outer_folds == 5).all() and (result.n_resamples==5000).all()
    comparison = pd.read_csv(OUT/'results/paired_AB_bootstrap_endpoint_comparison.csv')
    legacy = pd.read_csv(OUT/'results/paired_AB_bootstrap_pooled_diagnostic_legacy.csv')
    for row in comparison.itertuples():
        metric = 'EF@20' if row.metric=='EF_macro@20' else row.metric
        original = legacy[(legacy.model==row.model)&(legacy.reference==row.reference)&(legacy.metric==metric)].iloc[0]
        for field in ['delta_p025','delta_median','delta_p975','n_valid']:
            np.testing.assert_allclose(getattr(row,'legacy_pooled_'+field),original[field])
    return len(result)


def check_decisions():
    protocol = read('protocol.json')
    decision = read('P23_construction_decision.json')
    assert protocol['time'] < decision['time'] <= read('plan_amendment_freeze.json')['time']
    summary = pd.read_csv(HARD/'decision_stability_summary.csv',dtype={'pool':str}).set_index('pool')
    detail = pd.read_csv(HARD/'decision_stability_members.csv',dtype={'pool':str})
    split_detail = pd.read_csv(HARD/'split_half_detail.csv.gz',dtype={'pool':str})
    split_summary = pd.read_csv(HARD/'split_half_summary.csv',dtype={'pool':str})
    candidates = pd.read_csv(HARD/'decision_stability_all_candidates.csv.gz',dtype={'pool':str})
    members = [pd.read_csv(OUT/'bootstrap'/f'member_{b:02d}.csv.gz',float_precision='round_trip').set_index('key') for b in range(20)]
    for pool in protocol['decision_pools']:
        p = pd.read_csv(OUT/'predictions'/f'{pool}_P1_train02_predictions.csv',float_precision='round_trip')
        nominal = p.vhat.to_numpy(); ix = ordered_independent(nominal,p.key); star=ix[0]
        a = np.array([m.loc[p.key,'vhat'].to_numpy() for m in members])
        orders = np.array([ordered_independent(row,p.key) for row in a])
        ranks = np.argsort(orders,axis=1)+1
        rec = summary.loc[pool]; df = detail[detail.pool==pool].sort_values('member')
        forward = a[:,star]-a.min(axis=1); reverse=nominal[orders[:,0]]-nominal[star]
        gaps = np.array([row[idx[1]]-row[idx[0]] for row,idx in zip(a,orders)])
        np.testing.assert_allclose(df.decision_regret,forward)
        np.testing.assert_allclose(df.reverse_regret,reverse)
        np.testing.assert_allclose(df.member_best_second_gap,gaps)
        np.testing.assert_array_equal(df.nominal_rank,ranks[:,star])
        assert rec.nominal_rank_median==np.median(ranks[:,star])
        assert rec.nominal_rank_min==ranks[:,star].min() and rec.nominal_rank_max==ranks[:,star].max()
        for k in [5,20]:
            assert rec[f'nominal_top{k}_frequency']==(ranks[:,star]<=k).mean()
        for array, prefix in [(forward,'decision_regret'),(reverse,'reverse_regret'),(gaps,'member_best_second_gap')]:
            for q, label in [(.5,'p50'),(.9,'p90'),(.95,'p95'),(1,'max')]:
                np.testing.assert_allclose(rec[prefix+'_'+label],np.quantile(array,q),atol=1e-12)
        assert rec.near_optimal_plateau == (len(set(orders[:,0]))>1 and max(forward.max(),reverse.max())<=.1)
        c = candidates[candidates.pool==pool].set_index('key').loc[p.key]
        np.testing.assert_array_equal(c.rank_min,ranks.min(axis=0))
        np.testing.assert_array_equal(c.rank_max,ranks.max(axis=0))
        np.testing.assert_allclose(c.rank_median,np.median(ranks,axis=0))
        np.testing.assert_allclose(c.top20_frequency,(ranks<=20).mean(axis=0))
        # Independently rebuild three preregistered partitions and all 100 single pairs.
        for split in [0,499,999]:
            left=protocol['left_halves'][split];right=sorted(set(range(20))-set(left))
            comparisons={'single_member':[(a[i],a[j],orders[i],orders[j]) for i in left for j in right]}
            v,w=a[left].mean(axis=0),a[right].mean(axis=0)
            comparisons['bagged_half10']=[(v,w,ordered_independent(v,p.key),ordered_independent(w,p.key))]
            for method,pairs in comparisons.items():
                quantities=[]
                for v,w,oi,oj in pairs:
                    overlap=len(set(oi[:20])&set(oj[:20]))
                    quantities.append([oi[0]==oj[0],overlap/20,overlap/(40-overlap),
                                       ((w[oi[0]]-w.min())+(v[oj[0]]-v.min()))/2])
                expected=np.mean(quantities,axis=0)
                row=split_detail[(split_detail.pool==pool)&(split_detail.split==split)&(split_detail.method==method)].iloc[0]
                cols=['argmin_agreement','top20_overlap_fraction','top20_jaccard','symmetric_cross_table_decision_regret']
                np.testing.assert_allclose(row[cols].astype(float),expected,atol=1e-12)
    assert len(split_detail)==8000 and len(set(map(tuple,protocol['left_halves'])))==1000
    for row in split_summary.itertuples():
        rows=split_detail[(split_detail.pool==row.pool)&(split_detail.method==row.method)]
        for col in ['argmin_agreement','top20_overlap_fraction','top20_jaccard','symmetric_cross_table_decision_regret']:
            np.testing.assert_allclose(getattr(row,col),rows[col].mean(),atol=1e-12)
    single=split_summary[split_summary.method=='single_member'].set_index('pool')
    bag=split_summary[split_summary.method=='bagged_half10'].set_index('pool').loc[single.index]
    checks=[(bag.top20_overlap_fraction-single.top20_overlap_fraction).mean()>=.05-1e-12,
            (bag.top20_overlap_fraction>=single.top20_overlap_fraction-1e-12).all(),
            (bag.argmin_agreement>=single.argmin_agreement-1e-12).all(),
            (bag.symmetric_cross_table_decision_regret<=single.symmetric_cross_table_decision_regret+1e-12).all()]
    assert decision['construction']==('bagged_mean_20' if all(checks) else 'single_full_fit')
    assert all(decision['checks'].values())==all(checks)
    assert decision['no_EF_RMSE_or_truth_used'] and not decision['P23_retraining_executed']
    # Every family concentration record sums to its stated Top-k and uses pool backgrounds.
    families=read('element_families.json')
    family_detail=pd.read_csv(HARD/'family_concentration_detail.csv',dtype={'pool':str})
    for row in family_detail.itertuples():
        counts=json.loads(row.family_counts);assert sum(counts.values())==row.k
        shares=np.array(list(counts.values()))/row.k
        np.testing.assert_allclose(row.HHI,np.square(shares).sum())
        np.testing.assert_allclose(row.effective_family_count,1/row.HHI)
        np.testing.assert_allclose(row.dominant_share,max(shares))
        np.testing.assert_allclose(row.dominant_share_over_pool_share,row.dominant_share/row.dominant_pool_share)
    assert len(families)==52 and len(family_detail)==4*21*2*4
    return dict(pools=4,member_decisions=80,split_half_partitions=1000,
                independent_partition_spotchecks=12,construction=decision['construction'])


def main():
    protected = check_protection()
    main_table=check_main_table()
    intervals=check_bootstrap(main_table)
    decisions=check_decisions()
    assert Budget().count()==914
    receipt=dict(time=now(),passed=True,P0_1=True,P0_2=True,P0_3=True,P0_4=True,
        no_new_fits=True,fit_count_before=914,fit_count_after=914,remaining_reserved_for_P23=86,
        protected_files_unchanged=protected,core_training_code_unchanged=True,
        old_pooled_diagnostic_preserved=True,main_table_rows=13,per_fold_rows=65,
        bootstrap_comparison_rows=intervals,literal_bootstrap_check_resamples=5000,
        decision_checks=decisions,
        code_hashes={p.name:sha(p) for p in CODE.glob('*.py') if p.name in (
            'report.py','hardening_tables.py','decision_stability.py','hardening_report.py',
            'hardening_audit.py','test_hardening.py','audit.py')},
        plan_amendment_freeze_sha256=sha(HARD/'plan_amendment_freeze.json'),
        report_sha256=sha(ROOT/'codex/P1_HARDENING_REPORT.md'))
    dump(HARD/'hardening_audit.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('code_hashes','report_sha256')},ensure_ascii=False))


if __name__=='__main__':
    main()
