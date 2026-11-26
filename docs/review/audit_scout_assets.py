"""Read-only data and stored-matrix audit; no model training or solver calls.

Does not reconstruct split seeds, inspect external labels, import Kaiwu, authorize
services, or execute P2/P3 entry points. Writes only this review's own evidence.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / '00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date'
OLD = ROOT / '03_代码'
OUT = ROOT / 'artifacts/codex_review'


def violation(df):
    values = np.column_stack([df.e_form - .21, 1.4 - df.gap,
                              df.gap - 3.1, 5.73 - df.vbm, df.cbm - 4.50])
    return np.square(np.maximum(values, 0) / .5).sum(axis=1)


def to_ising(q):
    n = len(q)
    block = (q + q.T) / 8
    diagonal = np.diag(block).copy()
    np.fill_diagonal(block, 0)
    result = np.zeros((n + 1, n + 1))
    result[:-1, :-1] = -block
    result[-1, :-1] = result[:-1, -1] = -(block.sum(axis=0) + diagonal)
    return result, float(block.sum() + 2 * diagonal.sum())


def matrix_audit(pool, matrix, lam, joint=False):
    elements = sorted(set(pool.A) | set(pool.B))
    ei = {v: i for i, v in enumerate(elements)}
    xi = {'O3': 0, 'NO2': 1, 'FO2': 2}
    left = np.asarray([ei[v] for v in pool.A])
    right = np.asarray([52 + ei[b] * 3 + xi[x] if joint else 52 + ei[b]
                        for b, x in zip(pool.B, pool.X)])
    n = 208 if joint else 104
    expected = np.diag(np.full(n, -lam))
    for start, stop in [(0, 52), (52, n)]:
        expected[start:stop, start:stop] += np.triu(np.full((stop-start, stop-start), 2*lam), 1)
    expected[left, right] += pool.vhat.to_numpy()
    energy = matrix[left, left] + matrix[right, right] + matrix[left, right] + matrix[right, left]
    result = {'shape': list(matrix.shape), 'all_upper_triangular': bool(np.all(matrix == np.triu(matrix))),
              'independent_reconstruction_max_abs_diff': float(np.max(np.abs(expected-matrix))),
              'all_feasible_states': len(pool),
              'feasible_energy_plus_2lambda_max_abs_diff': float(np.max(np.abs(energy+2*lam-pool.vhat))),
              'table_nonnegative': bool((pool.vhat >= 0).all()),
              'lambda': lam, 'stored_table_minimum': float(pool.vhat.min())}
    j, bias = to_ising(matrix)
    states = -np.ones((len(pool), n+1), dtype=np.float64)
    states[:, -1] = 1
    states[np.arange(len(pool)), left] = 1
    states[np.arange(len(pool)), right] = 1
    ising_energy = -np.einsum('bi,ij,bj->b', states, j, states, optimize=True)
    result['ising_offset'] = bias
    result['ising_absmax'] = float(np.abs(j).max())
    result['ising_energy_plus_offset_max_abs_diff'] = float(np.max(np.abs(ising_energy+bias-energy)))
    if not joint:
        scale = 127/np.abs(j).max()
        rounded = np.rint(j*scale)
        rounded_energy = -np.einsum('bi,ij,bj->b', states, rounded, states, optimize=True)
        minimum = rounded_energy.min()
        result['uniform_8bit'] = {'scale': float(scale), 'coefficient_unique_before': len(np.unique(j)),
                                  'coefficient_unique_after': len(np.unique(rounded)),
                                  'AB_couplings_rounded_to_zero': int((rounded[:52,52:104] == 0).sum()),
                                  'AB_coupling_unique_after': np.unique(rounded[:52,52:104]).tolist(),
                                  'feasible_energy_unique_after': len(np.unique(rounded_energy)),
                                  'feasible_energy_range_after': [float(rounded_energy.min()),float(rounded_energy.max())],
                                  'feasible_minimum_tie_count': int((rounded_energy==minimum).sum()),
                                  'stored_original_best_quantized_rank': int((rounded_energy<rounded_energy[np.argmin(pool.vhat)]).sum())+1,
                                  'best_second_best_gap': float(np.sort(pool.vhat)[1]-np.sort(pool.vhat)[0]),
                                  'smallest_positive_gap_anywhere': float(np.diff(np.sort(pool.vhat))[np.diff(np.sort(pool.vhat))>0].min())}
    return result


def main():
    report = {'kind': 'independent audit of existing assets, no new solutions'}
    expected = json.loads((DATA/'sha256_public.json').read_text())
    report['public_hash_checks'] = {n: hashlib.sha256((DATA/n).read_bytes()).hexdigest()==s
                                  for n,s in expected.items()}
    tr = pd.read_csv(DATA/'02_castelli_train.csv')
    va = pd.read_csv(DATA/'03_castelli_val.csv')
    ho = pd.read_csv(DATA/'04_castelli_test_holdout.csv')
    report['data'] = {}
    for key, df in [('train',tr),('val',va)]:
        report['data'][key] = {'rows':len(df), 'columns':len(df.columns),
                               'V_zero':int((df.V==0).sum()), 'V_below2':int((df.V<2).sum()),
                               'V_recompute_max_abs_diff':float(np.max(np.abs(violation(df)-df.V))),
                               'gap_zero':int((df.gap==0).sum())}
    pair = lambda df: set(zip(df.A,df.B))
    ps = [pair(x) for x in [tr,va,ho]]
    report['AB_split'] = {'group_counts':list(map(len,ps)),
                          'pairwise_disjoint':not any(ps[i]&ps[j] for i in range(3) for j in range(i))}
    full = pd.concat([tr[ho.columns],va[ho.columns],ho],ignore_index=True)
    report['full_grid'] = {'rows':len(full),'unique_triples':full.groupby(['A','B','X']).ngroups,
                            'A_unique':full.A.nunique(),'B_unique':full.B.nunique(),'X_unique':full.X.nunique(),
                            'id_complete':set(full.id)==set(range(18928))}
    pools = {s:pd.read_csv(DATA/n) for s,n in [('07','07_castelli_q2_pool.csv'),('08','08_castelli_q3_pool.csv'),
                                               ('11','11_castelli_q2_pool_blind.csv'),('12','12_castelli_q3_pool_blind.csv')]}
    report['pool_membership'] = {'07':set(pools['07'].id)==set(full[full.X=='NO2'].id),
                                 '08':set(pools['08'].id)==set(full[full.X.isin(['O3','NO2','FO2'])].id),
                                 '11':set(pools['11'].id)==set(pools['07'].id)&set(ho.id),
                                 '12':set(pools['12'].id)==set(pools['08'].id)&set(ho.id)}
    old2 = json.loads((OLD/'p2_report.json').read_text())
    old3 = json.loads((OLD/'p3_report.json').read_text())
    report['stored_P2_matrix'] = matrix_audit(pd.read_csv(OLD/'p2_pool_predictions.csv'),
                                             np.load(OLD/'p2_qubo_matrix.npy',allow_pickle=False),old2['lambda'])
    report['stored_P3_matrix'] = matrix_audit(pd.read_csv(OLD/'p3_pool_predictions.csv'),
                                             np.load(OLD/'p3_qubo_matrix_joint.npy',allow_pickle=False),old3['lambda'],True)
    report['old_SA_reports_not_reexecuted'] = ['P2','P3','precision_experiment']
    OUT.mkdir(exist_ok=True,parents=True)
    (OUT/'stored_asset_audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps(report,indent=2,ensure_ascii=False))
    assert all(report['public_hash_checks'].values())
    assert report['AB_split']['pairwise_disjoint']
    assert all(report['pool_membership'].values())
    assert all(report[k]['independent_reconstruction_max_abs_diff']<1e-10
               and report[k]['feasible_energy_plus_2lambda_max_abs_diff']<1e-10 for k in ['stored_P2_matrix','stored_P3_matrix'])


if __name__ == '__main__':
    main()
