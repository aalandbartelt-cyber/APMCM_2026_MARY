"""Read-only mathematical and preservation checks. No fits, SA or remote calls."""
from pathlib import Path
import sys, json, itertools, hashlib
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'03_求解/D/p2_v2'))
from representation import construct

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
freeze=json.loads((ROOT/'codex/p2_rescue1/freeze.json').read_text())
for name,h in freeze['protected'].items():
    assert sha(ROOT/name)==h,name
checks={'protected_files':len(freeze['protected'])}
assert sha(ROOT/'artifacts/p1_v21/fit_ledger.jsonl')==freeze['fit_ledger_sha256']
checks['fit_ledger_unchanged']=True

# Exhaustive synthetic instances verify real-valued global and local claims.
rng=np.random.default_rng(92811);cases=0
for degenerate in [False,True]:
    for _ in range(8):
        W=rng.uniform(0,10,(3,3)) if not degenerate else np.ones((3,3))
        mask=rng.random((3,3))>.5;mask[0,0]=True
        m=W[mask].min();R=np.ptp(W[mask]);scale=R or 1.
        C=np.where(mask,W-m,scale);u=C.min(1);v=(C-u[:,None]).min(0)
        tr=max(C.min(0).max(),C.min(1).max())
        tc=max((C-v[None,:]).min(0).max(),(C-u[:,None]).min(1).max())
        t=max(tr,tc);lam=1.1*(t if t>0 else scale*2**-20)
        for enc in ['raw','rc']:
            J,meta,Q=construct(W,mask,enc,lam/scale)
            X=np.array(list(itertools.product([0,1],repeat=6)),int)
            S=np.c_[2*X-1,np.ones(len(X),int)]
            E=-(S@J*S).sum(1)+meta['offset']
            r=X[:,:3].sum(1);s=X[:,3:].sum(1);legal=(r==1)&(s==1)
            allowed=legal & mask[X[:,:3].argmax(1),X[:,3:].argmax(1)]
            assert abs(E[allowed].min())<1e-11
            assert E[~allowed].min()>1e-12
            for k,x in enumerate(X):
                if legal[k]:continue
                neighbors=np.sum(X!=x,axis=1)==1
                assert E[neighbors].min()<E[k]-1e-12,(enc,degenerate,k)
            cases+=1
checks['synthetic_exhaustive_cases']=cases

rec=json.loads((ROOT/'codex/p2_rescue1/selection_receipt.json').read_text())
assert rec['selected'] is None and rec['status']=='NO_ELIGIBLE_CONFIGURATION'
for row in rec['configurations']:
    z=np.load(ROOT/row['matrix_file']);K=z['J'];W=z['W'];mask=z['allowed']
    assert sha(ROOT/row['matrix_file'])==row['matrix_sha256']
    E=np.zeros((52,52),np.int64)
    for i in range(52):
        for j in range(52):
            s=-np.ones(105,np.int64);s[[i,52+j,104]]=1
            E[i,j]=-s@K@s
    minimum=E[mask].min();reg=W[(E==minimum)&mask].max()-W[mask].min()
    assert abs(reg-row['worst_ground_regret'])<1e-12
    cert=json.loads((ROOT/'artifacts/p2_rescue1/representations'/f'{row["id"]}.certificate.json').read_text())
    s=np.r_[2*np.array(cert['witness'])-1,1]
    assert -s@K@s==cert['witness_energy']<=minimum
checks['rescue_direct_onehot_energies_checked']=5408
checks['rejection_witnesses_checked']=2
checks['new_fits']=0;checks['new_SA']=0;checks['new_CIM']=0
print(json.dumps(checks,indent=2))
