"""Diagnose recorded old-baseline predictions; no fitting or holdout access.

Run after replay_scout_p1.py. All labels come from public 02/03. Bootstrap
resamples AB clusters within the observed fold-2 tail; it is conditional.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / '00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date'
OUT = ROOT / 'artifacts/codex_review/scout_p1_replay'


def tau(frame):
    value = kendalltau(frame.V, frame.pred).statistic if len(frame) > 1 else np.nan
    return float(value) if np.isfinite(value) else None


def summarize(frame, call):
    tail = frame[frame.V < 2]
    result = dict(call=call, n=len(frame), n_tail=len(tail),
                  n_tail_AB=tail.groupby(['A', 'B']).ngroups,
                  RMSE=float(np.sqrt(np.mean((frame.V-frame.pred)**2))),
                  tau_all=tau(frame), tau_tail=tau(tail), tail_by_x={}, top_k={})
    for x, sub in tail.groupby('X'):
        result['tail_by_x'][x] = dict(n=len(sub), v_range=[float(sub.V.min()), float(sub.V.max())],
                                     pred_range=[float(sub.pred.min()), float(sub.pred.max())],
                                     tau=tau(sub), mean_pred_minus_actual=float((sub.pred-sub.V).mean()))
    for k in (20, 50, 100):
        sub = frame.iloc[np.argsort(frame.pred.to_numpy())[:k]]
        result['top_k'][str(k)] = dict(tail_hits=int((sub.V < 2).sum()),
                                      mean_true_V=float(sub.V.mean()), min_true_V=float(sub.V.min()),
                                      regret=float(sub.V.min()-frame.V.min()))
    return result


def main():
    train = pd.read_csv(DATA/'02_castelli_train.csv')
    val = pd.read_csv(DATA/'03_castelli_val.csv')
    frames, stats = [], []
    for call in range(6):
        with np.load(OUT/f'prediction_call_{call}.npz', allow_pickle=False) as saved:
            source = val if call == 0 else train
            frame = source.iloc[saved['index']].copy()
            frame['pred'] = np.expm1(saved['log_prediction'])
        frames.append(frame)
        stats.append(summarize(frame, call))
        if call:
            frame['fold'] = call-1
            frame.to_csv(OUT/f'fold{call-1}_oof.csv', index=False)
    (OUT/'baseline_diagnostics.json').write_text(json.dumps(dict(val=stats[0], folds=stats[1:]), indent=2))
    tail = frames[3].query('V < 2').copy()
    counts = {name: dict(pairs=0, concordant=0, discordant=0, ties=0)
              for name in ('within_X', 'between_X')}
    records = tail[['X', 'V', 'pred']].to_records(index=False)
    for i, a in enumerate(records):
        for b in records[i+1:]:
            group = counts['within_X' if a.X == b.X else 'between_X']
            sign = np.sign((a.V-b.V)*(a.pred-b.pred))
            group['pairs'] += 1
            group['concordant' if sign > 0 else 'discordant' if sign < 0 else 'ties'] += 1
    for group in counts.values():
        group['concordant_minus_discordant'] = group['concordant']-group['discordant']
    clusters = [sub for _, sub in tail.groupby(['A', 'B'], sort=True)]
    rng = np.random.default_rng(20261126)
    boot = []
    for _ in range(5000):
        draw = pd.concat([clusters[i] for i in rng.integers(len(clusters), size=len(clusters))])
        value = tau(draw)
        if value is not None:
            boot.append(value)
    counts.update(AB_cluster_bootstrap_95pct=np.quantile(boot, [.025, .975]).tolist(),
                  bootstrap_seed=20261126, bootstrap_replicates=5000,
                  tail_predicted_below2=int((tail.pred < 2).sum()), tail_n=len(tail),
                  bootstrap_scope='existing fold2 tail, conditional diagnostic; not new model or population guarantee')
    (OUT/'fold2_error_analysis.json').write_text(json.dumps(counts, indent=2))
    names = ['p1_lgbm_baseline.txt', 'p1_feature_importance.csv', 'element_descriptors.csv']
    checks = {}
    for name in names:
        old = ROOT/'03_代码'/name
        new = OUT/name
        checks[name] = dict(sha256=hashlib.sha256(new.read_bytes()).hexdigest(),
                            byte_identical=new.read_bytes() == old.read_bytes())
    (OUT/'byte_identity.json').write_text(json.dumps(checks, indent=2))
    assert all(row['byte_identical'] for row in checks.values())
    print(json.dumps(dict(byte_identity=checks, fold2=counts), indent=2))


if __name__ == '__main__':
    main()
