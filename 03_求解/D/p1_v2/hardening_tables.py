"""Aggregate already-recorded metrics; no estimator or fitting dependency."""
import json
import numpy as np
import pandas as pd


def build_main_tables(allmetrics, nested, summary_metrics):
    rows = []
    choices = {r['fold']: r for r in nested}
    for kind, protocol in [('registered_candidate', 'outer'), ('fixed_baseline', 'baseline')]:
        for original in allmetrics[allmetrics.protocol == protocol].to_dict('records'):
            row = dict(original)
            fold = int(row['domain'].rsplit('_', 1)[1])
            row.update(row_kind=kind, fold=fold, selection_identity=row['route'],
                       selected_numeric_route=choices[fold]['numeric'],
                       selected_screen_route=choices[fold]['screen'],
                       used_by_numeric_procedure=(kind == 'registered_candidate' and row['route'] == choices[fold]['numeric']),
                       used_by_screen_procedure=(kind == 'registered_candidate' and row['route'] == choices[fold]['screen']))
            if kind == 'fixed_baseline':
                row['feature_set'] = 'A/B/X additive one-hot' if row['route'] == 'additive_ridge' else 'none'
            rows.append(row)
    for mode in ('numeric', 'screen'):
        for choice in nested:
            row = dict(choice[mode + '_result'])
            row.update(route='nested_' + mode, row_kind='nested_procedure', fold=choice['fold'],
                       selection_identity=choice[mode], selected_numeric_route=choice['numeric'],
                       selected_screen_route=choice['screen'], used_by_numeric_procedure=mode == 'numeric',
                       used_by_screen_procedure=mode == 'screen')
            rows.append(row)
    detail = pd.DataFrame(rows).sort_values(['row_kind', 'route', 'fold']).reset_index(drop=True)
    detail['k'] = 20
    detail['h'] = detail['hits@20'].astype(int)
    detail['screen_event'] = 'V<=2'
    assert not detail.duplicated(['route', 'fold']).any()
    assert (detail.groupby('route').size() == 5).all()
    np.testing.assert_allclose(detail['EF@20'], (detail.h / detail.k) / (detail.M / detail.N))
    main = summary_metrics(detail, ['route', 'row_kind', 'feature_set']).rename(columns={'RMSE_pooled': 'RMSE'})
    for i, row in main.iterrows():
        g = detail[detail.route == row['route']].sort_values('fold')
        for source, target in [('N', 'N_per_fold'), ('M', 'M_per_fold'), ('h', 'h_per_fold'),
                               ('selection_identity', 'selection_identity_per_fold'),
                               ('selected_numeric_route', 'nested_numeric_per_fold'),
                               ('selected_screen_route', 'nested_screen_per_fold')]:
            main.loc[i, target] = json.dumps(g[source].tolist(), separators=(',', ':'))
        main.loc[i, 'M_evaluated_sum'] = int(g.M.sum())
        main.loc[i, 'total_screen_budget'] = 100
    main['aggregation'] = 'pooled RMSE; equal mean of five fold-specific Top-20 EF'
    return main, detail
