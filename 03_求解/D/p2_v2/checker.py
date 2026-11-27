"""Independent certificate checker: direct integer spin energies, no builder import."""
import time
import numpy as np

def direct(J,X):
    """X is business bits; fixed reference +1. Includes symmetric double counting."""
    X=np.atleast_2d(X).astype(np.int64)
    S=np.concatenate([2*X-1,np.ones((len(X),1),dtype=np.int64)],axis=1)
    return -np.sum((S@J)*S,axis=1,dtype=np.int64)

def reconstruct(J):
    assert J.dtype.kind in 'iu' and np.array_equal(J,J.T)
    assert np.max(np.abs(J))<=32767 and len(J)<=105
    n=len(J)-1;zero=np.zeros((1,n),np.int64);c=int(direct(J,zero)[0])
    basis=np.eye(n,dtype=np.int64);single=direct(J,basis);l=single-c
    pairs=[(i,j) for i in range(n) for j in range(i+1,n)]
    rows=np.zeros((len(pairs),n),np.int64)
    for z,(i,j) in enumerate(pairs):rows[z,i]=rows[z,j]=1
    energies=direct(J,rows);q=np.zeros((n,n),np.int64)
    for en,(i,j) in zip(energies,pairs):q[i,j]=en-single[i]-single[j]+c
    return c,l,q

def cumulative(v): return np.r_[np.int64(0),np.cumsum(np.sort(np.asarray(v,dtype=np.int64)),dtype=np.int64)]

def certify(J,mask,node_limit=1000000,seconds=600):
    start=time.monotonic();na,nb=mask.shape;n=na+nb
    try:
        c,l,q=reconstruct(J)
        assert n+1==len(J)
        X=np.zeros((na*nb,n),np.int64)
        for i in range(na):
            for j in range(nb):X[i*nb+j,i]=X[i*nb+j,na+j]=1
        E=direct(J,X).reshape(na,nb);opt=int(E[mask].min())
        ans=dict(status='UNKNOWN',best_allowed_energy=opt,nodes=0,seconds=0.,witness=None,unclosed_classes=[])
        forbidden=np.argwhere((~mask)&(E<=opt))
        if len(forbidden):
            i,j=forbidden[0];x=np.zeros(n,np.int64);x[i]=x[na+j]=1
            ans.update(status='COUNTEREXAMPLE',reason='forbidden_onehot_not_above_allowed_min',witness=x.tolist(),witness_energy=int(direct(J,x)[0]));return finish(ans,start)
        # A concrete witness is decisive. Never infer a counterexample from a loose bound.
        for x in [np.zeros(n,np.int64),np.ones(n,np.int64),np.r_[np.ones(na,np.int64),np.zeros(nb,np.int64)],np.r_[np.zeros(na,np.int64),np.ones(nb,np.int64)]]:
            en=int(direct(J,x)[0])
            if (x[:na].sum()!=1 or x[na:].sum()!=1) and en<=opt:
                ans.update(status='COUNTEREXAMPLE',reason='direct_illegal_witness',witness=x.tolist(),witness_energy=en);return finish(ans,start)
        la,lb=cumulative(l[:na]),cumulative(l[na:])
        aa=cumulative(q[:na,:na][np.triu_indices(na,1)]);bb=cumulative(q[na:,na:][np.triu_indices(nb,1)]);ab=cumulative(q[:na,na:].ravel())
        bounds=[]
        for r in range(na+1):
            for s in range(nb+1):
                if (r,s)==(1,1):continue
                lower=int(c+la[r]+lb[s]+aa[r*(r-1)//2]+bb[s*(s-1)//2]+ab[r*s]);bounds.append([r,s,lower])
                if lower<=opt:ans['unclosed_classes'].append([r,s])
        ans['cardinality_bounds']=bounds
        if not ans['unclosed_classes']:
            ans.update(status='CERTIFIED',reason='all_cardinality_bounds_strict');return finish(ans,start)
        # Deterministic integer B&B over each unresolved cardinality class.
        weights=np.abs(l)+np.abs(q+q.T).sum(axis=1)
        order=sorted(range(n),key=lambda i:(-int(weights[i]),i));qs=q+q.T
        remaining=[]
        for r,s in ans['unclosed_classes']:
            stack=[(0,0,0,int(c),np.zeros(n,np.int64),l.copy())]
            while stack:
                if ans['nodes']>=node_limit or time.monotonic()-start>=seconds:
                    ans.update(reason='certificate_budget_exhausted',pending_nodes=len(stack),current_class=[r,s]);return finish(ans,start)
                depth,ar,bs,val,x,adjust=stack.pop();ans['nodes']+=1
                free=order[depth:];fa=[i for i in free if i<na];fb=[i for i in free if i>=na]
                ra=r-ar;sb=s-bs
                if ra<0 or sb<0 or ra>len(fa) or sb>len(fb):continue
                lower=val+int(np.sort(adjust[fa])[:ra].sum())+int(np.sort(adjust[fb])[:sb].sum())
                ea=[qs[i,j] for z,i in enumerate(fa) for j in fa[z+1:]]
                eb=[qs[i,j] for z,i in enumerate(fb) for j in fb[z+1:]]
                ec=[qs[i,j] for i in fa for j in fb]
                lower+=int(np.sort(ea)[:ra*(ra-1)//2].sum())+int(np.sort(eb)[:sb*(sb-1)//2].sum())+int(np.sort(ec)[:ra*sb].sum())
                if lower>opt:continue
                if depth==n:
                    actual=int(direct(J,x)[0]);assert actual==val
                    if actual<=opt:
                        ans.update(status='COUNTEREXAMPLE',reason='branch_witness',witness=x.tolist(),witness_energy=actual);return finish(ans,start)
                    continue
                i=order[depth];xx=x.copy();xx[i]=1;ll=adjust.copy();ll+=qs[i]
                stack.append((depth+1,ar+int(i<na),bs+int(i>=na),val+int(adjust[i]),xx,ll))
                stack.append((depth+1,ar,bs,val,x.copy(),adjust.copy()))
        ans.update(status='CERTIFIED',reason='exhaustive_integer_branch_closure',unclosed_classes=[])
        return finish(ans,start)
    except Exception as exc:
        return dict(status='IMPLEMENTATION_ERROR',reason=repr(exc),seconds=time.monotonic()-start)

def finish(ans,start):
    ans['seconds']=time.monotonic()-start
    return ans
