"""Bounded finer var split and algebraic item elimination. No SA/hardware."""
from pathlib import Path
import os,sys,json,hashlib
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/p2_research_20261128/split_resolution'

def analyze(path):
    z=np.load(path);J=np.rint(z['J']/z['delta']).astype(np.int64);idx=z['indices'];n=len(idx)
    assert n==105
    if np.array_equal(idx,np.arange(n)):
        L=J[:n,:n].copy();offset=0;assert not J[n:,n:].any()
        for i in range(n,len(J)):
            links=np.flatnonzero(J[i,:n]);assert len(links)==2;a,b=links;u,v=J[i,links]
            eff=(abs(int(u+v))-abs(int(u-v)))//2
            assert 2*eff==abs(int(u+v))-abs(int(u-v))
            L[a,b]+=eff;L[b,a]+=eff;offset-=abs(int(u+v))+abs(int(u-v))
        rng=np.random.default_rng(1172)
        for _ in range(100):
            s=rng.choice([-1,1],size=n);aux=np.where(J[n:,:n]@s>=0,1,-1);full=np.r_[s,aux]
            assert -full@J@full == -s@L@s+offset
        label='exact conditional minimization over independent degree-2 auxiliaries'
    else:
        lo=np.r_[0,idx[:-1]+1];hi=idx+1;L=np.zeros((n,n),dtype=np.int64)
        for i in range(n):
            for j in range(n):
                if i!=j:L[i,j]=J[lo[i]:hi[i],lo[j]:hi[j]].sum()
        label='coherent-copy restriction only; full-space alignment NOT certified'
    pool=np.load(ROOT/'artifacts/p23_v2/pool_11.npz');values=pool['vhat'][:,:,0];mask=pool['allowed'][:,:,0]
    X=np.zeros((2704,104),dtype=np.int64)
    for i in range(52):
        for j in range(52):X[i*52+j,i]=X[i*52+j,52+j]=1
    S=np.c_[2*X-1,np.ones(2704,dtype=np.int64)];E=-np.einsum('bi,ij,bj->b',S,L,S).reshape(52,52)
    ground=mask&(E==E[mask].min());vmin=values[mask].min()
    return dict(id=path.stem,physical_spins=len(J),max_J=int(np.abs(J).max()),scope=label,
        allowed_ground_regret_max=float((values[ground]-vmin).max()),allowed_ground_count=int(ground.sum()),
        forbidden_onehot_gap=int(E[~mask].min()-E[mask].min()),effective_matrix=L.tolist())

def main():
    OUT.mkdir(exist_ok=False)
    (OUT/'registration.json').write_text(json.dumps(dict(
        grid='var only, raw/rc x increments0.25/0.5; resource estimator fits550',
        followup='After coarse delta1/2 representation errors; exploratory no sampling',
        audit='all 2704 coherent states; item exact auxiliary elimination; retain var alignment uncertainty',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2))
    import kaiwu as kw
    sys.path.insert(0,str(ROOT/'configs'));from kaiwu_license import KAIWU_USER_ID,KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID,sdk_code=KAIWU_SDK_CODE)
    import requests
    def no_network(*a,**k):raise RuntimeError('Network prohibited for local probes')
    requests.sessions.Session.request=no_network
    paths=list((ROOT/'artifacts/p2_research_20261128/split_followup').glob('float*.npz'))
    for encoding in ['raw','rc']:
        J=np.load(ROOT/f'artifacts/p2_dual_rescue/inputs/{encoding}_J.npy')
        for delta in [.25,.5]:
            K,idx=kw.preprocess.perform_precision_adaption_split(J.copy(),param_bit=8,min_increment=delta,round_to_increment=True,method='var')
            path=OUT/f'float_{encoding}_var_{delta}.npz'
            with path.open('xb') as f:np.savez_compressed(f,J=K,indices=idx,delta=delta)
            paths.append(path)
    result=[]
    for path in paths:
        r=analyze(path);result.append(r);print(json.dumps({k:v for k,v in r.items() if k!='effective_matrix'}),flush=True)
    with (OUT/'audit.json').open('x') as f:json.dump(result,f,indent=2)

if __name__=='__main__':main()
