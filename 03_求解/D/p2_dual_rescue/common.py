"""Local records for the explicitly authorized sequential dual rescue."""
from pathlib import Path
import sys, json, hashlib, subprocess, os
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'03_求解/D/p2_v2'
sys.path.insert(0,str(BASE))
from p2_common import write_new, read, sha, now, tie, serial
OUT=ROOT/'artifacts/p2_dual_rescue'
REG=ROOT/'codex/p2_dual_rescue'
CODE=Path(__file__).resolve().parent
PROTOCOL=ROOT/'codex/P2_DUAL_RESCUE_PROTOCOL_20261128.md'

def save_array(path, array):
    with Path(path).open('xb') as f:
        np.save(f,array,allow_pickle=False);f.flush();os.fsync(f.fileno())

def verify_registration(commit):
    assert len(commit)==40
    for name in ['codex/P2_DUAL_RESCUE_PROTOCOL_20261128.md','codex/p2_dual_rescue/registration.json']:
        assert subprocess.check_output(['git','show',f'{commit}:{name}'],cwd=ROOT)==(ROOT/name).read_bytes()
    reg=read(REG/'registration.json')
    for name,h in {**reg['protected'],**reg['code_hashes'],**reg['input_hashes']}.items():
        assert sha(ROOT/name)==h,name
    return reg

def initialize_license():
    sys.path.insert(0,str(ROOT/'configs'))
    from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    import kaiwu as kw
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)

def pool():
    z=np.load(ROOT/'artifacts/p23_v2/pool_11.npz')
    W=z['vhat'][:,:,0];mask=z['allowed'][:,:,0]
    keys=np.array([[f'{a}|{b}|NO2' for b in z['B']] for a in z['A']])
    return W,mask,keys

def matrix_audit(ident,K,meta):
    # The certificate checker itself imports neither this module nor a builder.
    from checker import certify,direct
    from representation import metrics
    import pandas as pd
    W,mask,keys=pool();dest=OUT/'matrices';dest.mkdir(exist_ok=True)
    path=dest/f'{ident}.npz'
    with path.open('xb') as stream:
        np.savez_compressed(stream,J=K,W=W,allowed=mask,keys=keys)
    X=np.zeros((2704,104),np.int64)
    for i in range(52):
        for j in range(52):X[i*52+j,i]=X[i*52+j,52+j]=1
    E=direct(K,X).reshape(52,52)
    # A second direct full symmetric-spin evaluation has no polynomial conversion.
    S=np.c_[2*X-1,np.ones(2704,np.int64)]
    np.testing.assert_array_equal(E.ravel(),-np.einsum('bi,ij,bj->b',S,K,S))
    cert=certify(K,mask,node_limit=1000000,seconds=600)
    write_new(dest/f'{ident}.certificate.json',cert)
    m=metrics(W,mask,E,keys);g2='PASS' if m['worst_ground_regret']<=.1 else 'FAIL'
    overall=cert['status']
    if overall=='CERTIFIED' and g2=='FAIL':overall='COUNTEREXAMPLE'
    row=dict(id=ident,G1=cert['status'],G2=g2,status=overall,
             certificate_reason=cert.get('reason'),matrix_file=str(path.relative_to(ROOT)),
             matrix_sha256=sha(path),onehot_checked=2704,allowed_count=529,
             allowed_min=cert.get('best_allowed_energy'),witness_energy=cert.get('witness_energy'),
             meta=meta,**m)
    pd.DataFrame(dict(key=keys.ravel(),allowed=mask.ravel(),vhat=W.ravel(),energy=E.ravel())).to_csv(dest/f'{ident}.energies.csv',index=False,float_format='%.17g')
    write_new(dest/f'{ident}.audit.json',row)
    return row
