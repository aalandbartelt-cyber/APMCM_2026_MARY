"""Frozen policy, lineage and budget utilities for P1 v2.1."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/p1_v21'
DATA = ROOT / '00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date'
CODE = Path(__file__).resolve().parent
EPS = 2.0
SEED = 210026
X_ORDER = ['O3', 'NO2', 'FO2', 'N2O', 'N3', 'O2S', 'FNO']
ROUTES = ['R-raw', 'R-log', 'W-log', 'H-soft', 'S-eps', 'B-eps', 'L-single', 'L-hash4']
REG = ROUTES[:4]
COMPLEXITY = {'R-raw': 1, 'R-log': 1, 'W-log': 1, 'H-soft': 3, 'S-eps': 2, 'B-eps': 1, 'L-single': 1, 'L-hash4': 1}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def stable(value, namespace='tie'):
    return hashlib.sha256(f'P1v2.1/{namespace}/{value}'.encode()).hexdigest()


def jsonable(x):
    if isinstance(x, dict): return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [jsonable(v) for v in x]
    if isinstance(x, np.ndarray): return jsonable(x.tolist())
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (float, np.floating)): return float(x) if np.isfinite(x) else None
    if isinstance(x, (np.bool_,)): return bool(x)
    if isinstance(x, Path): return str(x.relative_to(ROOT)) if x.is_relative_to(ROOT) else x.name
    return x


def dump(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(jsonable(obj), ensure_ascii=False, indent=2) + '\n')
    os.replace(temp, path)


def load_data(prefix, labeled=False):
    """Label-bearing columns are read only by explicitly labeled 02/03 calls."""
    assert prefix in ('02', '03') or not labeled
    path = next(DATA.glob(prefix + '_*.csv'))
    cols = ['id', 'A', 'B', 'X'] + (['V', 'gap'] if labeled else [])
    d = pd.read_csv(path, usecols=cols)
    d['ab'] = d.A + '|' + d.B
    d['key'] = d.ab + '|' + d.X
    assert d.key.is_unique
    return d


def fold_ids(groups, n=5, namespace='outer/0'):
    ordered = sorted(set(groups), key=lambda g: stable(g, namespace))
    mapping = {g: i % n for i, g in enumerate(ordered)}
    return np.array([mapping[g] for g in groups], dtype=int)


class Budget:
    """Reserve before fitting; failures consume budget. Single-process writer."""
    def __init__(self):
        OUT.mkdir(parents=True, exist_ok=True)
        self.path = OUT / 'fit_ledger.jsonl'

    def entries(self):
        return [json.loads(s) for s in self.path.read_text().splitlines()] if self.path.exists() else []

    def count(self):
        return sum(r['event'] == 'start' for r in self.entries())

    def append(self, row):
        with self.path.open('a') as f:
            f.write(json.dumps(jsonable(dict(time=now(), **row)), ensure_ascii=False) + '\n')
            f.flush(); os.fsync(f.fileno())

    def reserve(self, **metadata):
        n = self.count() + 1
        if n > 1000: raise RuntimeError('Hard fit budget 1000 exhausted')
        self.append(dict(event='start', fit_number=n, **metadata))
        return n


def verify_public_hashes():
    expected = json.loads((DATA / 'sha256_public.json').read_text())
    got = {name: sha(DATA / name) for name in expected}
    assert got == expected, 'Public input changed'
    return got


def code_hashes():
    return {p.name: sha(p) for p in sorted(CODE.glob('*.py'))}
