"""Nonnegative two-register encodings; this module is not used by checker.py."""
import numpy as np
from p2_common import tie

def construct(W,mask,encoding,ratio=1.1):
    assert mask.any() and np.isfinite(W[mask]).all()
    na,nb=W.shape;m=float(W[mask].min());R=float(W[mask].max()-m)
    scale=R if R>0 else 1.;lam=ratio*scale
    C=np.where(mask,W-m,scale);u=np.zeros(na);v=np.zeros(nb)
    if encoding=='rc':u=C.min(axis=1);v=(C-u[:,None]).min(axis=0)
    D=C-u[:,None]-v[None,:]
    assert D.min()>=-1e-12
    Q=np.zeros((na+nb,na+nb));Q[:na,na:]=D
    for start,n,pot in [(0,na,u),(na,nb,v)]:
        for i in range(n):
            Q[start+i,start+i]=pot[i]-lam
            for j in range(i+1,n):Q[start+i,start+j]=2*lam
    n=na+nb;J=np.zeros((n+1,n+1));off=Q.copy();np.fill_diagonal(off,0)
    J[:n,:n]=-(off+off.T)/8
    J[:n,n]=J[n,:n]=-(np.diag(Q)/4+(off+off.T).sum(axis=1)/8)
    offset=float(np.trace(Q)/2+off.sum()/4+2*lam)
    theta_raw=max(C.min(axis=0).max(),C.min(axis=1).max())
    theta_rc=max((C-v[None,:]).min(axis=0).max(),(C-u[:,None]).min(axis=1).max())
    return J,dict(m=m,R=R,encoding_scale=scale,lam=lam,offset=offset,theta_raw=theta_raw,theta_rc=theta_rc),Q

def quantize(J,bits=8):
    bound=2**(bits-1)-1;peak=np.abs(J).max()
    factor=bound/peak if peak else 1.
    K=np.rint(J*factor).astype(np.int64)
    assert np.array_equal(K,K.T) and np.abs(K).max()<=bound
    return K,float(factor)

def polynomial(J):
    n=len(J)-1
    linear=4*(J[:n,:n].sum(axis=1)-np.diag(J[:n,:n]))-4*J[:n,n]
    quadratic=np.triu(-8*J[:n,:n],1)
    s=-np.ones(n+1,dtype=J.dtype);s[-1]=1
    c=-s@J@s
    return c,linear,quadratic

def legal_energies(J,na,nb):
    c,l,q=polynomial(J)
    return c+l[:na,None]+l[None,na:]+q[:na,na:]

def metrics(W,mask,E,keys):
    ids=np.flatnonzero(mask.ravel());w=W.ravel();e=E.ravel();key=np.asarray(keys).ravel()
    orig=sorted(ids,key=lambda z:(w[z],tie(key[z])));inte=sorted(ids,key=lambda z:(int(e[z]),tie(key[z])))
    k=min(20,len(ids));T=set(orig[:k]);cut=e[inte[k-1]]
    L={int(i) for i in ids if e[i]<cut};B={int(i) for i in ids if e[i]==cut};q=k-len(L)
    emin=e[inte[0]];ground=ids[e[ids]==emin];reg=w[ground]-w[orig[0]];R=w[ids].max()-w[ids].min()
    wcut=w[orig[k-1]];wtie=[int(i) for i in ids if w[i]==wcut]
    return dict(best_integer_energy=int(emin),ground_count=len(ground),ground_indices=ground.tolist(),worst_ground_regret=float(reg.max()),
        best_ground_regret=float(reg.min()),top20_retention=len(T.intersection(inte[:k]))/k,
        top20_min=(len(L&T)+max(0,q-len(B-T)))/k,top20_max=(len(L&T)+min(q,len(B&T)))/k,
        top20_original=[str(key[i]) for i in orig[:k]],top20_integer=[str(key[i]) for i in inte[:k]],
        original_boundary_keys=[str(key[i]) for i in wtie],integer_boundary_keys=[str(key[i]) for i in sorted(B)],
        integer_strict_before=len(L),integer_boundary_take=q,R=float(R),epsilon_over_R=.1/R if R else None,
        original_min=float(w[orig[0]]),original_best_keys=[str(key[i]) for i in ids if w[i]==w[orig[0]]])
