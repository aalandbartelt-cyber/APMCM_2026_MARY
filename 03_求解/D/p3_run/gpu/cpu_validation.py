"""Paired Kaiwu 1.4.4 CPU observations for the GPU qualification gate only."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import hashlib
import json
import socket
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'artifacts/p3_run/B/gpu_gate'
REG=json.loads((OUT/'preregistration.json').read_text())
FAMILIES=tuple(REG['families'])

def local_only(*args, **kw):
    raise RuntimeError('Only offline classical solves are permitted')

def prepare():
    socket.socket.connect=local_only
    global kw, matrices
    import kaiwu as kw
    matrices={}
    for family in FAMILIES:
        matrix=np.load(ROOT/'evidence/p3'/f'{family}.npz')['J']
        assert hashlib.sha256(matrix.astype('<i8').tobytes()).hexdigest()==REG['matrix_sha_i64'][family]
        matrices[family]=matrix.astype(float)

def sample(case):
    family,seed=case
    mat=matrices[family]
    solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=4.0*np.abs(mat).sum(1).max(),
        alpha=.99,cutoff_temperature=1e-4,iterations_per_t=len(mat),size_limit=1,rand_seed=seed,process_num=1)
    out=np.asarray(solver.solve(mat))
    if out.shape!=(1,len(mat)) or not np.isin(out,[-1,1]).all():
        raise ValueError('Malformed CPU output')
    return {'family':family,'seed':seed,'vector':out[0].astype(int).tolist()}

if __name__=='__main__':
    cases=[(fam,660001+1000*j+i) for j,fam in enumerate(FAMILIES) for i in range(REG['n_per_family'])]
    with (OUT/'cpu_vectors.jsonl').open('x') as sink, ProcessPoolExecutor(max_workers=4,initializer=prepare) as pool:
        for record in pool.map(sample,cases,chunksize=1):
            sink.write(json.dumps(record,separators=(',',':'))+'\n')
            sink.flush()
