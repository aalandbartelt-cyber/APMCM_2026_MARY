"""Label-free decision diagnostics from twenty existing prediction tables only.

No training, calibration, score optimization, model selection, or label loading.
The P23 construction policy is read from a protocol frozen before these results.
"""
import json
import numpy as np
import pandas as pd
from common import ROOT, OUT, stable, dump, sha, now

HARD = OUT / 'hardening'
METRICS = ['argmin_agreement', 'top20_overlap_fraction', 'top20_jaccard',
           'symmetric_cross_table_decision_regret']


def quantiles(values, prefix):
    a = np.asarray(values)
    return {prefix + '_' + name: float(value) for name, value in zip(
        ['min', 'p50', 'p90', 'p95', 'max'], np.quantile(a, [0, .5, .9, .95, 1]))}


def order_values(values, ties):
    return np.lexsort((ties, np.asarray(values)))


def decision_pair(a, b, order_a, order_b, k=20):
    """Symmetric regrets evaluate each chosen index on the other value table."""
    overlap = len(set(order_a[:k]) & set(order_b[:k]))
    ia, ib = order_a[0], order_b[0]
    return np.array([float(ia == ib), overlap/k, overlap/(2*k-overlap),
                     .5*((b[ia]-b[ib])+(a[ib]-a[ia]))])


def choose_construction(summary, protocol):
    single = summary[summary.method == 'single_member'].set_index('pool')
    bag = summary[summary.method == 'bagged_half10'].set_index('pool').loc[single.index]
    diff = bag[METRICS] - single[METRICS]
    tol = protocol['selection_rule']['numeric_tolerance']
    checks = {
        'macro_top20_overlap_gain_ge_0.05': bool(diff.top20_overlap_fraction.mean() >= .05-tol),
        'top20_not_worse_each_pool': bool((diff.top20_overlap_fraction >= -tol).all()),
        'argmin_not_worse_each_pool': bool((diff.argmin_agreement >= -tol).all()),
        'regret_not_worse_each_pool': bool((diff.symmetric_cross_table_decision_regret <= tol).all()),
    }
    return dict(construction='bagged_mean_20' if all(checks.values()) else 'single_full_fit',
                checks=checks, macro_top20_overlap_gain=float(diff.top20_overlap_fraction.mean()),
                decision_metrics_only=True, no_EF_RMSE_or_truth_used=True,
                differences=diff.reset_index().to_dict('records'))


def family_map(elements, provenance, protocol):
    groups = provenance[provenance.property == 'group'].set_index('element').value.to_dict()
    result = {}
    for el in elements:
        assigned = [family for family, names in protocol['element_families'].items()
                    if isinstance(names, list) and el in names]
        assert len(assigned) <= 1
        if assigned:
            result[el] = assigned[0]
        else:
            assert 3 <= groups[el] <= 12, ('Unregistered family', el, groups[el])
            result[el] = 'groups_3_to_12'
    return result


def concentration(labels, selected):
    background = pd.Series(labels).value_counts(normalize=True)
    counts = pd.Series(np.asarray(labels)[selected]).value_counts()
    share = counts / counts.sum()
    # Fixed lexicographic tie resolution only for naming the dominant family.
    dominant = sorted(share[share == share.max()].index)[0]
    hhi = float(np.square(share).sum())
    return dict(dominant_family=dominant, dominant_share=float(share[dominant]),
                HHI=hhi, effective_family_count=1/hhi,
                dominant_pool_share=float(background[dominant]),
                dominant_share_over_pool_share=float(share[dominant]/background[dominant]),
                family_counts=json.dumps(counts.sort_index().to_dict(), sort_keys=True))


def analyze_pool(pool, p, values, protocol, families):
    keys = p.key.to_numpy()
    ties = np.array([stable(key, 'tie') for key in keys])
    nominal = p.vhat.to_numpy()
    nominal_order = order_values(nominal, ties)
    orders = np.array([order_values(v, ties) for v in values])
    ranks = np.empty_like(orders)
    for b, order in enumerate(orders):
        ranks[b, order] = np.arange(1, len(keys)+1)
    nominal_ranks = np.empty(len(keys), int)
    nominal_ranks[nominal_order] = np.arange(1, len(keys)+1)
    opt = nominal_order[0]
    winners = orders[:, 0]
    forward = values[:, opt] - values[np.arange(len(values)), winners]
    reverse = nominal[winners] - nominal[opt]
    gaps = values[np.arange(len(values)), orders[:, 1]] - values[np.arange(len(values)), winners]
    rotating = len(set(winners)) > 1
    plateau = rotating and max(forward.max(), reverse.max()) <= protocol['plateau_tolerance_V']
    summary = dict(pool=pool, N=len(keys), n_members=len(values), nominal_minimizer=keys[opt],
        nominal_vhat=float(nominal[opt]), nominal_best_second_gap=float(nominal[nominal_order[1]]-nominal[opt]),
        nominal_rank_median=float(np.median(ranks[:, opt])), nominal_rank_min=int(ranks[:, opt].min()),
        nominal_rank_max=int(ranks[:, opt].max()), nominal_top5_frequency=float((ranks[:, opt] <= 5).mean()),
        nominal_top20_frequency=float((ranks[:, opt] <= 20).mean()),
        nominal_argmin_frequency=float((winners == opt).mean()), distinct_minimizers=len(set(winners)),
        **quantiles(forward, 'decision_regret'), **quantiles(reverse, 'reverse_regret'),
        **quantiles(gaps, 'member_best_second_gap'),
        plateau_tolerance_V=protocol['plateau_tolerance_V'], near_optimal_plateau=bool(plateau),
        interpretation='near-optimal plateau under registered surrogate tolerance' if plateau
                       else 'identity rotation; assess the reported surrogate costs' if rotating
                       else 'stable identity in observed members')
    members = [dict(pool=pool, member=b, winner=keys[winners[b]], winner_vhat=values[b, winners[b]],
        nominal_rank=int(ranks[b, opt]), nominal_top5=bool(ranks[b, opt] <= 5),
        nominal_top20=bool(ranks[b, opt] <= 20), decision_regret=forward[b], reverse_regret=reverse[b],
        member_best_second_gap=gaps[b]) for b in range(len(values))]
    candidates = p[['key', 'A', 'B', 'X']].copy()
    candidates.insert(0, 'pool', pool)
    candidates['A_family'] = candidates.A.map(families)
    candidates['B_family'] = candidates.B.map(families)
    candidates['AB_family'] = candidates.A_family + '/' + candidates.B_family
    candidates['nominal_rank'] = nominal_ranks
    candidates['nominal_vhat'] = nominal
    candidates['rank_median'] = np.median(ranks, axis=0)
    candidates['rank_min'] = ranks.min(axis=0)
    candidates['rank_max'] = ranks.max(axis=0)
    candidates['top5_frequency'] = (ranks <= 5).mean(axis=0)
    candidates['top20_frequency'] = (ranks <= 20).mean(axis=0)
    candidates['argmin_frequency'] = (ranks == 1).mean(axis=0)
    regrets = values - values[np.arange(len(values)), winners, None]
    for q, name in [(.5, 'p50'), (.9, 'p90'), (.95, 'p95'), (1, 'max')]:
        candidates['decision_regret_' + name] = np.quantile(regrets, q, axis=0)
    candidates['leading_candidate'] = (nominal_ranks <= 20) | (ranks.min(axis=0) <= 20)
    families_out = []
    for name, order in [('nominal', nominal_order)] + [(str(b), order) for b, order in enumerate(orders)]:
        for k in protocol['top_k']:
            for axis in protocol['family_concentration']['axes']:
                families_out.append(dict(pool=pool, member=name, k=k, axis=axis,
                                         **concentration(candidates[axis], order[:k])))
    # For each partition, single-model reference is all 100 cross-half pairs.
    pairwise = np.empty((len(values), len(values), len(METRICS)))
    for i in range(len(values)):
        for j in range(i, len(values)):
            pairwise[i, j] = pairwise[j, i] = decision_pair(values[i], values[j], orders[i], orders[j])
    split_rows = []
    universe = set(range(len(values)))
    for split, left in enumerate(protocol['left_halves']):
        right = sorted(universe-set(left))
        assert len(left) == len(right) == 10 and not set(left) & set(right)
        a, b = values[left].mean(axis=0), values[right].mean(axis=0)
        singles = pairwise[np.ix_(left, right)].mean(axis=(0, 1))
        bagged = decision_pair(a, b, order_values(a, ties), order_values(b, ties))
        for method, metrics in [('single_member', singles), ('bagged_half10', bagged)]:
            split_rows.append(dict(pool=pool, split=split, method=method, **dict(zip(METRICS, metrics))))
    mean20 = values.mean(axis=0)
    full_comparison = dict(pool=pool, nominal_argmin=keys[opt],
        mean20_argmin=keys[order_values(mean20, ties)[0]],
        **dict(zip(METRICS, decision_pair(nominal, mean20, nominal_order, order_values(mean20, ties)))),
        role='descriptive anchor; not a selection criterion')
    return summary, members, candidates, families_out, split_rows, full_comparison


def main():
    protocol_path = HARD / 'protocol.json'
    protocol_hash = sha(protocol_path)
    protocol = json.loads(protocol_path.read_text())
    assert protocol['no_new_fits'] and protocol['member_count'] == 20
    assert len(set(map(tuple, protocol['left_halves']))) == protocol['split_half_count'] == 1000
    assert len(list((OUT/'bootstrap').glob('member_*.csv.gz'))) == 20
    members = [pd.read_csv(OUT/'bootstrap'/f'member_{b:02d}.csv.gz', float_precision='round_trip').set_index('key')
               for b in range(20)]
    assert all(m.index.is_unique and list(m.columns) == ['vhat'] for m in members)
    pools = {pool: pd.read_csv(OUT/'predictions'/f'{pool}_P1_train02_predictions.csv',
                              usecols=['key', 'A', 'B', 'X', 'vhat'], float_precision='round_trip')
             for pool in protocol['decision_pools']}
    elements = sorted(set().union(*(set(p.A) | set(p.B) for p in pools.values())))
    families = family_map(elements, pd.read_csv(OUT/'element_provenance.csv'), protocol)
    dump(HARD/'element_families.json', families)
    sums, member_rows, candidate_frames, family_rows, split_rows, anchor_rows = [], [], [], [], [], []
    for pool, p in pools.items():
        assert p.key.is_unique
        values = np.array([m.loc[p.key, 'vhat'].to_numpy() for m in members])
        assert np.isfinite(values).all()
        a, b, c, d, e, f = analyze_pool(pool, p, values, protocol, families)
        sums.append(a); member_rows.extend(b); candidate_frames.append(c)
        family_rows.extend(d); split_rows.extend(e); anchor_rows.append(f)
    pd.DataFrame(sums).to_csv(HARD/'decision_stability_summary.csv', index=False)
    pd.DataFrame(member_rows).to_csv(HARD/'decision_stability_members.csv', index=False)
    candidates = pd.concat(candidate_frames, ignore_index=True)
    candidates.to_csv(HARD/'decision_stability_all_candidates.csv.gz', index=False)
    candidates[candidates.leading_candidate].sort_values(['pool', 'nominal_rank']).to_csv(
        HARD/'decision_stability_leading_candidates.csv', index=False)
    family_detail = pd.DataFrame(family_rows)
    family_detail.to_csv(HARD/'family_concentration_detail.csv', index=False)
    family_summary = []
    for (pool, k, axis), g in family_detail.groupby(['pool', 'k', 'axis']):
        base = g[g.member == 'nominal'].iloc[0]
        boots = g[g.member != 'nominal']
        row = dict(pool=pool, k=k, axis=axis, nominal_dominant_family=base.dominant_family,
            nominal_dominant_share=base.dominant_share, nominal_HHI=base.HHI,
            nominal_effective_family_count=base.effective_family_count,
            nominal_dominant_pool_share=base.dominant_pool_share,
            nominal_dominant_enrichment=base.dominant_share_over_pool_share)
        for metric in ('dominant_share', 'HHI', 'effective_family_count', 'dominant_share_over_pool_share'):
            row.update(quantiles(boots[metric], 'member_' + metric))
        family_summary.append(row)
    pd.DataFrame(family_summary).to_csv(HARD/'family_concentration_summary.csv', index=False)
    split_detail = pd.DataFrame(split_rows)
    split_detail.to_csv(HARD/'split_half_detail.csv.gz', index=False)
    split_summary = []
    for (pool, method), g in split_detail.groupby(['pool', 'method']):
        row = dict(pool=pool, method=method, n_partitions=len(g), n_underlying_members=20)
        for metric in METRICS:
            row[metric] = g[metric].mean()
            row.update(quantiles(g[metric], metric))
        split_summary.append(row)
    summary = pd.DataFrame(split_summary)
    summary.to_csv(HARD/'split_half_summary.csv', index=False)
    pd.DataFrame(anchor_rows).to_csv(HARD/'nominal_vs_mean20_diagnostic.csv', index=False)
    choice = choose_construction(summary, protocol)
    choice.update(time=now(), protocol_sha256=protocol_hash,
        split_half_summary_sha256=sha(HARD/'split_half_summary.csv'),
        scope='future P23_train02val03 only; original P1 outputs unchanged',
        dependence='1000 partitions reuse 20 empirical members, not 1000 independent experiments',
        extrapolation='10-vs-10 tests averaging; no direct independent validation of 20-member means',
        P23_retraining_executed=False, fit_count=914,
        recipe=protocol['future_P23_fit_recipe'])
    dump(HARD/'P23_construction_decision.json', choice)
    assert sha(protocol_path) == protocol_hash
    manifest = dict(time=now(), protocol_sha256=protocol_hash, no_new_fits=True,
        no_labels_used=True, member_files={p.name: sha(p) for p in (OUT/'bootstrap').glob('member_*.csv.gz')},
        files={p.name: sha(p) for p in HARD.glob('*') if p.is_file() and
               (p.suffix == '.csv' or p.name.endswith('.csv.gz') or p.name == 'P23_construction_decision.json')})
    dump(HARD/'decision_manifest.json', manifest)
    print(json.dumps({'decision_analysis_complete': True, 'construction': choice['construction'],
                      'checks': choice['checks'], 'new_fits': 0}))


if __name__ == '__main__':
    main()
