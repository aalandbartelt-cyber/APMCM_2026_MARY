"""Correct two probe harness issues, retaining every original probe output."""
from pathlib import Path
import os,sys,json,hashlib,itertools
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'artifacts/p2_research_20261128/sdk_probes'
OUT=ROOT/'artifacts/p2_research_20261128/split_followup'

def main():
    OUT.mkdir(exist_ok=False)
    (OUT/'registration.json').write_text(json.dumps(dict(
        reason='Original full probes used archived N8 instead of float input; toy var inverse requires individual states, not a batch.',
        action='Retain wrong-input and harness-error records. Replay saved toy matrices; split actual archived float inputs.',
        full_grid='raw/rc x item/var x increment1/2; no SA or hardware',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2))
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'));from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def no_network(*a,**k):raise RuntimeError('Network prohibited for local probes')
    requests.sessions.Session.request=no_network
    rows=[]
    for path in sorted(BASE.glob('split_var*.npz')):
        z=np.load(path);J=z['J'];a=z['input'];idx=z['indices'];X=np.array(list(itertools.product([-1,1],repeat=len(J))))
        Y=[];ok=[];errors={}
        for x in X:
            try:y=kw.preprocess.restore_split_solution(x,idx);Y.append(y);ok.append(True)
            except Exception as e:Y.append(x[idx]);ok.append(False);errors[type(e).__name__]=str(e)[:200]
        Y=np.array(Y);F=-np.einsum('bi,ij,bj->b',X,J,X);T=-np.einsum('bi,ij,bj->b',Y,a,Y)
        S=np.array(list(itertools.product([-1,1],repeat=3)));E=-np.einsum('bi,ij,bj->b',S,a,S);ground=F==F.min()
        aligned=np.array([all(np.all(x[lo:hi+1]==x[hi]) for lo,hi in zip(np.r_[0,idx[:-1]+1],idx)) for x in X])
        rows.append(dict(id=path.stem,spins=len(J),indices=idx.tolist(),
            all_ground_copies_aligned=bool(aligned[ground].all()),ground_original_regret_max=float(T[ground].max()-E.min()),
            restore_successes=sum(ok),total=len(X),restore_errors=errors,
            coherent_offset_range=[float((F[aligned]-T[aligned]).min()),float((F[aligned]-T[aligned]).max())]))
    for encoding in ['raw','rc']:
        path=ROOT/f'artifacts/p2_dual_rescue/inputs/{encoding}_J.npy';a=np.load(path)
        assert np.abs(a).max()>600
        for method in ['item','var']:
            for delta in [1.,2.]:
                name=f'float_{encoding}_{method}_{delta}';row=dict(id=name,input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),input_max=float(np.abs(a).max()))
                try:
                    b,idx=kw.preprocess.perform_precision_adaption_split(a.copy(),param_bit=8,min_increment=delta,round_to_increment=True,method=method)
                    with (OUT/(name+'.npz')).open('xb') as f:np.savez_compressed(f,J=b,indices=idx,delta=delta)
                    row.update(spins=len(b),max_scaled_J=float(np.abs(b/delta).max()),integral=bool(np.allclose(b/delta,np.rint(b/delta))),within550=len(b)<=550)
                except Exception as e:row.update(error=type(e).__name__+': '+str(e)[:200])
                rows.append(row)
    with (OUT/'results.json').open('x') as f:json.dump(rows,f,indent=2)
    for row in rows:print(json.dumps(row),flush=True)

if __name__=='__main__':main()
