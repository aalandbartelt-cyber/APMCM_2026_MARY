"""Run the registered CPU fallback after a recorded GPU gate; retain every raw return."""
import argparse
import csv
import hashlib
import json
import os
import socket
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True
import numpy as np

from register import ROOT, OUTPUT, FAMILIES, ANCHOR, json_bytes, digest, create

GATE = ROOT/'artifacts/p3_run/B/gpu_gate/decision.json'
REG = OUTPUT/'registration.json'
SEAL = ROOT/'evidence/p3'


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def forbid_network(*args, **kwargs):
    raise RuntimeError('The formal SA baseline is an offline operation.')


@lru_cache(maxsize=3)
def matrix_for(fam):
    with np.load(SEAL/(fam+'.npz'),allow_pickle=False) as model:
        return model['J'].astype(np.float64)


def load_manifest():
    spec = json.loads(REG.read_text())
    seed_bytes = (OUTPUT/'seeds.csv').read_bytes()
    assert digest(seed_bytes) == spec['formal_seed_manifest_sha256']
    assert digest((OUTPUT/'seed_history_sources.json').read_bytes()) == spec['seed_history_sources_sha256']
    anchor_bytes = subprocess.check_output(['git','-C',str(ROOT),'show',ANCHOR+':evidence/p3/receipt.json'])
    assert anchor_bytes == (SEAL/'receipt.json').read_bytes()
    assert digest(anchor_bytes) == spec['sealed_receipt_sha256']
    inputs = json.loads(anchor_bytes)['files']
    for filename in ('protocol.py', *(f+'.npz' for f in FAMILIES)):
        assert inputs['evidence/p3/'+filename] == digest((SEAL/filename).read_bytes())
    entries = [{k:(v if k=='family' else int(v)) for k,v in row.items()}
               for row in csv.DictReader(seed_bytes.decode().splitlines())]
    assert len(entries) == len({r['seed'] for r in entries}) == 900
    gate_seeds = {660001 + 1000*j+i for j in range(3) for i in range(160)}
    assert not gate_seeds.intersection(r['seed'] for r in entries)
    return entries


def tag(r):
    return f"{r['family']}_B{r['block']:02d}_R{r['restart']:03d}"


def save_raw(row, vectors):
    base = tag(row)
    final = OUTPUT/'vectors'/(base+'.npy')
    temp = final.with_suffix('.partial')
    with temp.open('xb') as f:
        np.save(f,vectors,allow_pickle=False)
        f.flush()
        os.fsync(f.fileno())
    os.link(temp, final)
    temp.unlink()
    return {'vector_path':str(final.relative_to(OUTPUT)),'sha256':digest(final.read_bytes()),
            'dtype':str(vectors.dtype),'shape':list(vectors.shape)}


def solve_one(item):
    row, cutoff_contract = item
    socket.socket.connect = forbid_network
    socket.socket.connect_ex = forbid_network
    import kaiwu as kw
    basename = tag(row)
    matrix = matrix_for(row['family'])
    t0 = float(4*np.max(np.sum(np.abs(matrix),axis=1)))
    cutoff = 1e-4 if cutoff_contract=='absolute' else t0*1e-4
    receipt = {**row,'started_utc':now(),'T0':t0,'cutoff':cutoff,'backend':'kaiwu_cpu4'}
    create(OUTPUT/'starts'/(basename+'.json'), json_bytes(receipt))
    try:
        solver = kw.classical.SimulatedAnnealingOptimizer(
            initial_temperature=t0,cutoff_temperature=cutoff,alpha=.99,
            iterations_per_t=len(matrix),rand_seed=row['seed'],size_limit=1,process_num=1)
        vectors = np.asarray(solver.solve(matrix))
        receipt.update(save_raw(row,vectors))
        if vectors.shape!=(1,len(matrix)) or not np.isin(vectors,(-1,1)).all():
            raise ValueError('Expected one complete bipolar spin vector')
        receipt['status']='RETURNED'
    except Exception as error:
        receipt.update(status='FAILED',error_type=type(error).__name__,message=str(error))
    receipt['finished_utc']=now()
    create(OUTPUT/'returns'/(basename+'.json'),json_bytes(receipt))
    return (basename,receipt['status'])


def run():
    import importlib.metadata as metadata
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration-sha256',required=True)
    parser.add_argument('--cutoff-contract',choices=('relative','absolute'),required=True)
    args = parser.parse_args()
    assert args.registration_sha256 == digest(REG.read_bytes())
    correction = json.loads((OUTPUT/'registration_addendum.json').read_text())
    assert correction['registration_sha256']==args.registration_sha256
    assert args.cutoff_contract==correction['formal_cutoff_contract']=='absolute'
    entries = load_manifest()
    gate_data = GATE.read_bytes()
    gate = json.loads(gate_data)
    if gate.get('gate_passed') is not False or gate.get('formal_backend')!='kaiwu_cpu4':
        raise SystemExit('CPU fallback requires recorded GPU gate failure and kaiwu_cpu4 decision')
    assert metadata.version('kaiwu') == '1.4.4'
    for name in ('vectors','starts','returns'):
        (OUTPUT/name).mkdir(exist_ok=True)
    start_doc = {'started_utc':now(),'registration_sha256':args.registration_sha256,
                 'gate_sha256':digest(gate_data),'cutoff_contract':args.cutoff_contract,
                 'registration_addendum_sha256':digest((OUTPUT/'registration_addendum.json').read_bytes()),
                 'backend':'kaiwu_cpu4','sdk':'kaiwu '+metadata.version('kaiwu'),
                 'numpy':np.__version__,'python':sys.version,'max_workers':4,
                 'source_sha256': digest(Path(__file__).read_bytes())}
    launch=OUTPUT/'launch.json'
    if launch.exists():
        previous=json.loads(launch.read_text())
        for key in ('gate_sha256','cutoff_contract','registration_sha256','source_sha256'):
            assert previous[key]==start_doc[key],key
    else:
        create(launch,json_bytes(start_doc))
    pending=[]
    for row in sorted(entries,key=lambda r:(r['restart'],r['block'],FAMILIES.index(r['family']))):
        base=tag(row)
        result=OUTPUT/'returns'/(base+'.json')
        started=OUTPUT/'starts'/(base+'.json')
        if result.exists():
            old=json.loads(result.read_text())
            assert {k:old[k] for k in row}==row
            if old['status']=='RETURNED':
                assert old['sha256']==digest((OUTPUT/old['vector_path']).read_bytes())
        elif started.exists():
            raise SystemExit('An interrupted restart cannot be repeated automatically: '+base)
        else:
            pending.append((row,args.cutoff_contract))
    counts={}
    print('Executing',len(pending),'registered restarts',flush=True)
    with ProcessPoolExecutor(max_workers=4) as pool:
        for idx,(base,status) in enumerate(pool.map(solve_one,pending,chunksize=1),1):
            counts[status]=counts.get(status,0)+1
            if idx%30==0 or status!='RETURNED':
                print(now(),idx,counts,flush=True)
    print('Finished',counts,flush=True)


if __name__=='__main__':
    run()
