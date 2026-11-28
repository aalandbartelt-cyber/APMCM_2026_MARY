"""Archive outputs from the exact same CUDA routine if both validation gates passed."""
import argparse
import json
import os
import socket
import sys
from pathlib import Path

from run_formal import GATE, ROOT, OUTPUT, REG, matrix_for, now, tag, load_manifest, save_raw, forbid_network
from register import FAMILIES, digest, create, json_bytes


def run():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration-sha256',required=True)
    args=parser.parse_args()
    assert args.registration_sha256==digest(REG.read_bytes())
    gate=json.loads(GATE.read_text())
    if gate.get('gate_passed') is not True or gate.get('formal_backend')!='cuda':
        raise SystemExit('GPU gate has not admitted CUDA')
    addition=OUTPUT/'registration_addendum.json'
    assert json.loads(addition.read_text())['formal_cutoff_contract']=='absolute'
    entries=load_manifest()
    gpu_dir=Path(__file__).resolve().parents[1]/'gpu'
    sys.path.insert(0,str(gpu_dir))
    socket.socket.connect=forbid_network
    from gpu_runner import Kernel, run_vectors
    kernel=Kernel()
    for name in ('vectors','starts','returns'):
        (OUTPUT/name).mkdir(exist_ok=True)
    launch={'started_utc':now(),'registration_sha256':args.registration_sha256,
            'registration_addendum_sha256':digest(addition.read_bytes()),'gate_sha256':digest(GATE.read_bytes()),
            'backend':'cuda','cutoff_contract':'absolute','source_sha256':digest(Path(__file__).read_bytes()),
            'gpu_runner_sha256':digest((gpu_dir/'gpu_runner.py').read_bytes()),
            'serial_sa_cu_sha256':digest((gpu_dir/'serial_sa.cu').read_bytes()),
            'batching':'one CUDA thread per independent restart, all 300 independent seeds per slice'}
    create(OUTPUT/'launch.json',json_bytes(launch))
    for family in FAMILIES:
        family_rows=[r for r in entries if r['family']==family]
        m=matrix_for(family)
        initial=float(4*abs(m).sum(axis=1).max())
        starts=[]
        for r in family_rows:
            fact={**r,'started_utc':now(),'T0':initial,'cutoff':0.0001,'backend':'cuda'}
            create(OUTPUT/'starts'/(tag(r)+'.json'),json_bytes(fact))
            starts.append(fact)
        result,meta=run_vectors(kernel,m,[r['seed'] for r in family_rows])
        assert result.shape==(len(family_rows),490)
        create(OUTPUT/('gpu_schedule_'+family+'.json'),json_bytes(meta))
        for k,r in enumerate(starts):
            record={**r,**save_raw(r,result[k:k+1]),'status':'RETURNED','finished_utc':now()}
            create(OUTPUT/'returns'/(tag(r)+'.json'),json_bytes(record))


if __name__=='__main__':
    run()
