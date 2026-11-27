"""Render manuscript tables from existing P1 results; never import fitting code."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '00_赛题与规则/官方发布/2026论文规范与模板/APMCM LaTeX 模板/tables'
RESULTS = ROOT / 'artifacts/p1_v21/results'
HARDENING = ROOT / 'artifacts/p1_v21/hardening'
manifest = {}

def number(v, digits=4):
    return '--' if pd.isna(v) else f'{v:.{digits}f}'

def table(name, label, caption, headers, rows, source, note='', columns=None):
    columns = columns or ('@{}l' + 'r' * (len(headers)-1) + '@{}')
    env = 'tabularx' if 'X' in columns else 'tabular'
    table_start = f'\\begin{{{env}}}' + ('{\\linewidth}' if env == 'tabularx' else '') + f'{{{columns}}}\n'
    body = '\n'.join(' & '.join(map(str, row)) + r'\\' for row in rows)
    text = ('\\par\n\\begin{table}[H]\n\\centering\n\\begin{threeparttable}\n'
            f'\\caption{{{caption}}}\\label{{{label}}}\n'
            + table_start
            + '\\toprule\n' + ' & '.join(headers) + r'\\' + '\n\\midrule\n'
            + body + f'\n\\bottomrule\n\\end{{{env}}}\n')
    if note:
        text += '\\begin{tablenotes}[flushleft]\n\\item[] ' + note + '\n\\end{tablenotes}\n'
    text += '\\end{threeparttable}\n\\end{table}\n\\par\n'
    path = OUT / (name + '.tex')
    path.write_text(text)
    manifest[name] = {'label': label, 'sources': source, 'rows': rows,
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

main = pd.read_csv(RESULTS / 'P1_final_experiment_table.csv').set_index('route')
names = {'additive_ridge': 'Additive Ridge', 'mean': 'Training mean',
         'random_hash': 'Fixed random', 'nested_numeric': 'Nested numerical selection',
         'nested_screen': 'Nested screening selection'}
order = ['H-soft', 'R-raw', 'R-log', 'W-log', 'B-eps', 'S-eps', 'L-single',
         'L-hash4', 'additive_ridge', 'mean', 'random_hash']
rows = []
for name in order:
    r = main.loc[name]
    rows.append([names.get(name, name), number(r.RMSE),
                 number(r['EF_{V<=2}@20_mean']), str(int(r.hits20_sum)), number(r['NDCG@20_mean'])])
table('main_results', 'tab:mainresults', 'Grouped-validation prediction and screening',
      ['Method', 'RMSE', 'EF@20', 'Hits/100', 'NDCG@20'], rows,
      ['results/P1_final_experiment_table.csv'],
      note=r'EF/NDCG average five fold-specific lists for $V\le2$; hits have budget 100. Dashes denote methods without original-scale predictions.')

table('nested', 'tab:nested', 'Performance of nested model-selection procedures',
      ['Procedure', 'RMSE', 'Mean EF@20', 'Hits/100'],
      [[name, number(main.loc[key,'RMSE']), number(main.loc[key,'EF_{V<=2}@20_mean']), str(int(main.loc[key,'hits20_sum']))]
       for key,name in [('nested_numeric','Numerical selection'),('nested_screen','Screening selection')]],
      ['results/P1_final_experiment_table.csv'],
      note='Model selection uses only the inner training folds. Numerical selection chooses H-soft in every outer fold.')

d = pd.read_csv(RESULTS / '03_development_results.csv')
table('development_results', 'tab:development', 'Development-set results at $k=20$',
      ['Method', 'RMSE', 'Hits/20', 'EF@20', 'NDCG@20'],
      [[r.route, number(r.RMSE), str(int(r['hits@20'])), number(r['EF_{V<=2}@20']), number(r['NDCG@20'])]
       for _, r in d.iterrows()], ['results/03_development_results.csv'],
      note=r'Development pool: $N=3{,}969$, $M=41$. NDCG breaks the enrichment tie.')

fold = main.loc['H-soft']
vectors = [json.loads(fold[c]) for c in ['N_per_fold', 'M_per_fold', 'h_per_fold']]
table('fold_counts', 'tab:folds', 'H-soft evaluation-pool counts at the primary budget',
      ['Outer fold', '$N$', '$M$', '$h_{20}$', 'EF@20'],
      [[str(i+1), str(n), str(m), str(h), number((h/20)/(m/n))]
       for i, (n,m,h) in enumerate(zip(*vectors))], ['results/P1_final_experiment_table.csv'],
      note=r'Event: $V\le2$. Mean EF averages these five pools; it does not use a pooled Top-20 list.')

cal = pd.read_csv(RESULTS / 'oof_calibration_consistency.csv')
cal = cal[cal.fold.astype(str) == 'pooled']
table('calibration', 'tab:calibration', 'Probability calibration on pooled outer-fold predictions',
      ['Method', 'Brier score', 'Mean probability', 'Intercept', 'Slope'],
      [[r.route, number(r.brier,6), number(r.mean_probability,4),
        number(r.calibration_intercept), number(r.calibration_slope)] for r in cal.itertuples()],
      ['results/oof_calibration_consistency.csv'],
      note=r'Prevalence: 0.01137. Ideal diagnostic intercept/slope: 0/1. These are evaluation diagnostics.')

query = pd.read_csv(RESULTS / 'query_seed_stability.csv')
qrows = [['Primary assignment', number(main.loc['L-hash4','EF_{V<=2}@20_mean']), '20.0', '20--20']]
for seed in [1,2]:
    q = query[query.route == f'L-hash4-seed{seed}']
    qrows.append([f'Assignment {seed}', number(q['EF@20'].mean()), number(q.top20_overlap.mean(),1),
                  f'{int(q.top20_overlap.min())}--{int(q.top20_overlap.max())}'])
table('query', 'tab:query', 'Sensitivity of four-query ranking to group assignment',
      ['Assignment', 'Mean EF@20', 'Mean overlap', 'Overlap range'], qrows,
      ['results/query_seed_stability.csv', 'results/P1_final_experiment_table.csv'],
      note='Overlap is out of 20, relative to the primary assignment within each outer fold.')

st = pd.read_csv(HARDENING / 'decision_stability_summary.csv')
table('nominal_stability', 'tab:nominal', 'Nominal-candidate ranks and surrogate costs across 20 fitted tables',
      ['Pool', 'Median rank', 'Rank range', 'Top-20 rate', '$R_{.95}$', '$\widetilde R_{.95}$'],
      [[f'{int(r.pool):02d}', number(r.nominal_rank_median,1), f'{r.nominal_rank_min}--{r.nominal_rank_max}',
        number(r.nominal_top20_frequency,2), number(r.decision_regret_p95), number(r.reverse_regret_p95)]
       for r in st.itertuples()], ['hardening/decision_stability_summary.csv'],
      note=r'Nominal minimum: La--Ti--$\mathrm{NO_2}$. Regret uses predicted objectives.')

st = pd.read_csv(HARDENING / 'split_half_summary.csv')
rows = []
for pool in [7,8,11,12]:
    a = st[(st.pool==pool) & (st.method=='single_member')].iloc[0]
    b = st[(st.pool==pool) & (st.method=='bagged_half10')].iloc[0]
    rows.append([f'{pool:02d}', number(a.argmin_agreement,3), number(b.argmin_agreement,3),
                 number(a.top20_overlap_fraction,3), number(b.top20_overlap_fraction,3),
                 number(a.symmetric_cross_table_decision_regret,3), number(b.symmetric_cross_table_decision_regret,3)])
table('stability', 'tab:stability', 'Single-member and ten-member-average stability under split-half comparisons',
      ['Pool', '$A_s$', '$A_b$', '$O_s$', '$O_b$', '$R_s$', '$R_b$'], rows,
      ['hardening/split_half_summary.csv'],
      note=r'$A$: minimum agreement; $O$: Top-20 overlap; $R$: symmetric regret. Subscripts $s/b$: single/mean of ten. Means use 1,000 partitions of 20 models.')

stress = pd.read_csv(RESULTS / 'stress_summary.csv')
table('stress', 'tab:stress', 'Exclusion-protocol results for R-log and S-eps',
      ['Protocol', 'Method', 'Valid EF pools', 'RMSE', 'Mean EF@20'],
      [[{'element':'Element','target':'Target region','xleave':'X family'}[r.protocol], r.route,
        f'{int(r.EF_defined_evaluations)}/{int(r.evaluations)}', number(r.RMSE_pooled), number(r['EF@20_mean'])]
       for _,r in stress.iterrows()], ['results/stress_summary.csv'],
      columns='@{}X l r r r@{}',
      note=r'Protocol-level evidence for R-log/S-eps. Pools with $M=0$ have undefined EF; numerical evaluation retains them.')

diag = pd.read_csv(RESULTS / 'diagnostic_summary.csv')
fr=[]
for fs in ['F0','F3']:
    r = diag[(diag.protocol=='feature') & (diag.feature_set==fs)].iloc[0]
    fr.append(['R-log', {'F0':'Basic (40)','F3':'Chemistry/geometry (292)'}[fs],number(r.RMSE_pooled),number(r['EF@20_mean'])])
fr.append(['R-log','Full (336)',number(main.loc['R-log','RMSE']),number(main.loc['R-log','EF_{V<=2}@20_mean'])])
fr.append(['H-soft','Full (336)',number(main.loc['H-soft','RMSE']),number(main.loc['H-soft','EF_{V<=2}@20_mean'])])
for key,label in [('minus_electronic','Without electronic'),('minus_geometry','Without geometry'),('minus_xstats','Without X statistics')]:
    r=diag[(diag.protocol=='ablation') & (diag.feature_set==key)].iloc[0]
    fr.append(['H-soft',label,number(r.RMSE_pooled),number(r['EF@20_mean'])])
table('features', 'tab:features', 'Descriptor comparisons and reverse ablations',
      ['Method','Descriptor set','RMSE','Mean EF@20'],fr,
      ['results/diagnostic_summary.csv','results/P1_final_experiment_table.csv'],columns='@{}l X r r@{}',
      note='Ablations also remove the block\'s derived quantities and missing indicators.')

paired = pd.read_csv(RESULTS / 'paired_AB_bootstrap_5000.csv')
label_names = {'H-soft':'H-soft minus R-log','S-eps':'S-eps minus B-eps','L-single':'L-single minus L-hash4',
               'R-log':'R-log: full minus 292 entries','H-soft_minus_electronic':'H-soft: without electronic',
               'H-soft_minus_geometry':'H-soft: without geometry','H-soft_minus_xstats':'H-soft: without X statistics'}
rows=[]
for _,r in paired.iterrows():
    rows.append([label_names[r.model], 'EF@20' if r.metric.startswith('EF') else 'RMSE',
                 number(r.delta_point), '$['+number(r.delta_p025)+', '+number(r.delta_p975)+']$'])
table('paired', 'tab:paired', 'Paired differences with conditional 95\% bootstrap intervals',
      ['Comparison','Measure','Difference','95\% interval'], rows,
      ['results/paired_AB_bootstrap_5000.csv'],columns='@{}X l r r@{}',
      note=r'All 5,000 resamples are valid. Intervals condition on fitted predictions and prior selection; no multiplicity adjustment. Ablation differences subtract full H-soft.')

(Path(__file__).parent/'table_source_map.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f'Generated {len(manifest)} tables from existing results.')
