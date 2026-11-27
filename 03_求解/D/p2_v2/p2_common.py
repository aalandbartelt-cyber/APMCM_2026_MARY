"""P2 v2 immutable records, input protection, and externally pinned selection."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CODE = Path(__file__).resolve().parent
P1 = ROOT / 'artifacts/p1_v21'
P23 = ROOT / 'artifacts/p23_v2'
OUT = ROOT / 'artifacts/p2_v2'
REG = ROOT / 'codex/p2_v2'
DATA = ROOT / '00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date'
RECEIPT = 'codex/p2_v2/selection_receipt.json'

def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(o):
    if isinstance(o, dict): return {str(k): clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)): return [clean(v) for v in o]
    if isinstance(o,np.ndarray): return clean(o.tolist())
    if isinstance(o,np.integer): return int(o)
    if isinstance(o,np.bool_): return bool(o)
    if isinstance(o,(float,np.floating)): return float(o) if np.isfinite(o) else None
    if isinstance(o,Path): return str(o.relative_to(ROOT)) if o.is_relative_to(ROOT) else str(o)
    return o
def serial(o): return (json.dumps(clean(o),sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()
def write_new(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f: f.write(serial(o));f.flush();os.fsync(f.fileno())
def append(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a') as f:
        f.write(json.dumps(clean(dict(time=now(),**o)),ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def read(p): return json.loads(Path(p).read_text())
def code_hashes(): return {str(p.relative_to(ROOT)):sha(p) for p in sorted(CODE.glob('*.py'))}
def tie(key): return hashlib.sha256(('P1v2.1/tie/'+str(key)).encode()).hexdigest()

def verify_inputs():
    freeze=read(REG/'input_freeze.json')
    for name,h in freeze['public_hashes'].items(): assert sha(DATA/name)==h, name
    for name,h in freeze['protected'].items(): assert sha(ROOT/name)==h, name
    assert sha(ROOT/'codex/P2_PLAN.md')==freeze['plan_sha256']
    for name,h in freeze['training_code'].items(): assert sha(ROOT/name)==h,name
    ledger=(P1/'fit_ledger.jsonl').read_bytes()
    assert hashlib.sha256(ledger[:freeze['ledger_initial_bytes']]).hexdigest()==freeze['ledger_initial_sha256']
    return freeze

def anchor(commit, require_selected=False):
    """No latest-file fallback. Caller must use the publicly announced commit."""
    assert commit and len(commit)==40, 'Explicit full anchored commit required'
    raw=subprocess.check_output(['git','show',f'{commit}:{RECEIPT}'],cwd=ROOT)
    assert raw==(ROOT/RECEIPT).read_bytes(),'Working receipt differs from git anchor'
    obj=json.loads(raw)
    for name,h in obj['code_hashes'].items(): assert sha(ROOT/name)==h, name
    for name,h in obj['input_hashes'].items(): assert sha(ROOT/name)==h, name
    for row in obj['configurations']:
        if row.get('matrix_file'): assert sha(ROOT/row['matrix_file'])==row['matrix_sha256']
    for row in obj['sa_matrices']:
        assert sha(ROOT/row['matrix_file'])==row['matrix_sha256']
    if require_selected: assert obj['selected'] is not None,'No certified hardware setting'
    return obj
