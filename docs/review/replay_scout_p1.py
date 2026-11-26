"""Replay the existing P1 baseline without changing its modeling choices.

Only redirects the output directory, limits CPU affinity, and records predictions
already produced by the original script. No holdout or service access.
"""
import ast
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/codex_review/scout_p1_replay'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if hasattr(os, 'sched_getaffinity'):
        os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    import lightgbm as lgb
    import numpy as np

    source = ROOT / '03_代码/p1_baseline.py'
    raw = source.read_bytes()
    tree = ast.parse(raw)
    replacements = 0
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'OUT' for t in node.targets):
            node.value = ast.Constant(str(OUT))
            replacements += 1
    assert replacements == 1
    ast.fix_missing_locations(tree)
    recorded = []
    original_predict = lgb.LGBMRegressor.predict

    def record_prediction(self, data, *args, **kwargs):
        result = original_predict(self, data, *args, **kwargs)
        recorded.append({'index': np.asarray(data.index, dtype=int),
                         'log_prediction': np.asarray(result).copy()})
        return result

    lgb.LGBMRegressor.predict = record_prediction
    scope = {'__name__': '__scout_baseline_replay__', '__file__': str(source)}
    try:
        exec(compile(tree, str(source), 'exec'), scope)
    finally:
        lgb.LGBMRegressor.predict = original_predict
    for i, entry in enumerate(recorded):
        np.savez(OUT / f'prediction_call_{i}.npz', **entry)
    metadata = {'source_sha256': hashlib.sha256(raw).hexdigest(),
                'changes': ['OUT redirected', 'CPU affinity limited to four cores',
                            'existing predict outputs recorded'],
                'best_iteration': int(scope['model'].best_iteration_),
                'feature_columns': list(scope['Xtr'].columns),
                'prediction_call_rows': [len(x['index']) for x in recorded]}
    (OUT / 'replay_metadata.json').write_text(json.dumps(metadata, indent=2))
    assert source.read_bytes() == raw


if __name__ == '__main__':
    main()
