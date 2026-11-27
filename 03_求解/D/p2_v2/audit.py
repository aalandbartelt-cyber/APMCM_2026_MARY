"""Table enumeration, representation audits, and deterministic pre-SA selection."""
import json
import importlib.util
import numpy as np
import pandas as pd
from p2_common import ROOT,CODE,P23,OUT,REG,read,write_new,sha,now,verify_inputs,code_hashes,tie
from representation import construct,quantize,legal_energies,metrics
from checker import certify,direct

def audit_one(pool,encoding,kind,J,W,mask,keys,meta,primary=False):
    dest=OUT/'representations';dest.mkdir(exist_ok=True,parents=True)
    ident=f'{pool}-{encoding}-{kind}';path=dest/f'{ident}.npz'
    np.savez_compressed(path,J=J,W=W,allowed=mask,keys=keys)
    E=legal_energies(J,*mask.shape)
    row=dict(id=ident,pool=pool,encoding=encoding,kind=kind,matrix_file=str(path.relative_to(ROOT)),matrix_sha256=sha(path),meta=meta)
    if J.dtype.kind in 'iu':
        # Independent direct evaluator checks every one-hot energy.
        na,nb=mask.shape;X=np.zeros((na*nb,na+nb),np.int64)
        for i in range(na):
            for j in range(nb):X[i*nb+j,i]=X[i*nb+j,na+j]=1
        np.testing.assert_array_equal(E,direct(J,X).reshape(mask.shape))
        cert=certify(J,mask,node_limit=1000000 if primary else 0,seconds=600 if primary else 30)
        row.update(metrics(W,mask,E,keys),certificate=cert['status'],certificate_reason=cert['reason'])
        write_new(dest/f'{ident}.certificate.json',cert)
    else:
        target=np.where(mask,W-meta['m'],meta['encoding_scale'])
        residual=E+meta['offset']-target
        assert np.max(np.abs(residual))<1e-8*max(1.,meta['encoding_scale'])
        row.update(float_equivalence_max_abs=float(np.max(np.abs(residual))),certificate='ANALYTIC_REAL_ONLY')
    data=pd.DataFrame(dict(key=keys.ravel(),allowed=mask.ravel(),vhat=W.ravel(),energy=E.ravel()))
    data.to_csv(dest/f'{ident}.energies.csv',index=False,float_format='%.17g')
    write_new(dest/f'{ident}.json',row)
    print(json.dumps(dict(audit=ident,status=row['certificate'],worst_regret=row.get('worst_ground_regret'))),flush=True)
    return row

def main():
    verify_inputs();assert (P23/'manifest.json').exists();assert not (REG/'selection_receipt.json').exists()
    OUT.mkdir(exist_ok=True)
    source=importlib.util.find_spec('kaiwu.preprocess._precision_adaption_mutate').origin
    mutate=dict(status='UNVERIFIED_GENERATION_CONTROL',certificate='UNKNOWN',
        reason='Installed 1.4.4 compiled API has no seed argument; complete internal RNG/tie contract cannot be verified from available source. No production mutate invocation.',
        binary_sha256=sha(source),version='1.4.4',parameters=dict(iterations=100,heuristic='greedy',decision='heuristic'),
        seeds=[240026,240027,240028,240029],first_output_generated=False)
    write_new(OUT/'mutate_control_audit.json',mutate)
    rows=[];primary=[];enum=[]
    for pool in ('07','11'):
        z=np.load(P23/f'pool_{pool}.npz');W=z['vhat'][:,:,0];mask=z['allowed'][:,:,0]
        keys=np.array([[f'{a}|{b}|NO2' for b in z['B']] for a in z['A']])
        ids=np.argwhere(mask);order=sorted(ids.tolist(),key=lambda ij:(W[tuple(ij)],tie(keys[tuple(ij)])))
        minimum=W[tuple(order[0])];enum.append(dict(pool=pool,n_allowed=int(mask.sum()),minimum=float(minimum),best_keys=keys[mask&(W==minimum)].tolist()))
        pd.DataFrame([dict(rank=n+1,key=keys[i,j],vhat=W[i,j],regret=W[i,j]-minimum) for n,(i,j) in enumerate(order)]).to_csv(OUT/f'enumeration_{pool}.csv',index=False,float_format='%.17g')
        for encoding in ('raw','rc'):
            J,meta,Q=construct(W,mask,encoding)
            # SDK converter is an additional contract, never the independent checker.
            from kaiwu.core import qubo_matrix_to_ising_matrix
            sdk,bias=qubo_matrix_to_ising_matrix(Q)
            np.testing.assert_allclose(J,sdk,rtol=1e-14,atol=1e-12)
            assert abs(bias+2*meta['lam']-meta['offset'])<1e-8
            rows.append(audit_one(pool,encoding,'float',J,W,mask,keys,meta))
            for bits in (4,6,8,10,12,16):
                K,scale=quantize(J,bits);kind=f'N{bits}'
                row=audit_one(pool,encoding,kind,K,W,mask,keys,dict(meta,quant_scale=scale),primary=pool=='11' and bits==8)
                rows.append(row)
                if pool=='11' and bits==8:primary.append(row)
            missing=dict(id=f'{pool}-{encoding}-M8',pool=pool,encoding=encoding,kind='M8',matrix_file=None,matrix_sha256=None,certificate='UNKNOWN',certificate_reason=mutate['reason'],generation_status=mutate['status'])
            rows.append(missing)
            if pool=='11':primary.append(missing)
            if meta['R']>0:
                for ratio in (.1,2.2):
                    L,mm,_=construct(W,mask,encoding,ratio)
                    rows.append(audit_one(pool,encoding,f'lambda{ratio}-float',L,W,mask,keys,mm))
                    K,scale=quantize(L)
                    rows.append(audit_one(pool,encoding,f'lambda{ratio}-N8',K,W,mask,keys,dict(mm,quant_scale=scale)))
            # Counterfactual preserves mask cost and lambda, not its own degenerate range.
            na,nb=mask.shape;C=np.where(mask,0.,meta['encoding_scale']);u=np.zeros(na);v=np.zeros(nb)
            if encoding=='rc':u=C.min(axis=1);v=(C-u[:,None]).min(axis=0)
            QQ=np.zeros((na+nb,na+nb));QQ[:na,na:]=C-u[:,None]-v[None,:]
            for start,n,p in [(0,na,u),(na,nb,v)]:
                for i in range(n):
                    QQ[start+i,start+i]=p[i]-meta['lam']
                    for j in range(i+1,n):QQ[start+i,start+j]=2*meta['lam']
            JJ,_=qubo_matrix_to_ising_matrix(QQ);factor=127/np.abs(J).max()
            K=np.rint(JJ*factor).astype(np.int64);realK,_=quantize(J)
            write_new(OUT/f'negative_control_{pool}_{encoding}.json',dict(matrix_equal=bool(np.array_equal(K,realK)),
                changed_entries=int(np.count_nonzero(K-realK)),onehot_energy_equal=bool(np.array_equal(legal_energies(K,na,nb),legal_energies(realK,na,nb))),scale=factor))
        # Zero-new-fit uncertainty, same mean target.
        members=z['members'][:,:,0,:][mask];reg=members-members.min(axis=0)
        nom=np.flatnonzero(W[mask]==minimum)[0]
        uncertainty=pd.DataFrame(dict(key=keys[mask],mean_vhat=W[mask],worst_regret=reg.max(axis=1),cvar90=np.sort(reg,axis=1)[:,-2:].mean(axis=1)))
        for quant in (.5,.9,.95):uncertainty[f'regret_p{int(100*quant)}']=np.quantile(reg,quant,axis=1)
        uncertainty.to_csv(OUT/f'uncertainty_{pool}.csv',index=False,float_format='%.17g')
    write_new(OUT/'enumeration.json',enum)
    write_new(OUT/'representation_audits.json',rows)
    eligible=[r for r in primary if r['certificate']=='CERTIFIED' and r['worst_ground_regret']<=.1]
    eligible.sort(key=lambda r:(r['worst_ground_regret'],-r['top20_min'],r['kind']!='N8',r['id']))
    chosen=eligible[0]['id'] if eligible else None
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'codex/P2_PLAN.md',REG/'input_freeze.json',P23/'manifest.json',P23/'pool_07.npz',P23/'pool_11.npz',OUT/'representation_audits.json']}
    allmat=[dict(id=r['id'],matrix_file=r.get('matrix_file'),matrix_sha256=r.get('matrix_sha256')) for r in rows if r.get('matrix_file') and r['kind'] in ('float','N8','M8')]
    receipt=dict(time=now(),status='SELECTED' if chosen else 'NO_ELIGIBLE_CONFIGURATION',selected=chosen,
        selected_matrix_sha256=next((r['matrix_sha256'] for r in primary if r['id']==chosen),None),
        configurations=primary,sa_matrices=allmat,selection_order=['CERTIFIED','worst_ground_regret<=0.1','min_worst_regret','max_tie_lower_retention','N8_before_M8','id'],
        code_hashes=code_hashes(),input_hashes=inputs,sa_started=False,cim_submitted=False,
        immutable_source='Must be committed; runtime requires exact published git commit.')
    write_new(REG/'selection_receipt.json',receipt)
    print(json.dumps(dict(selection=chosen,receipt_sha256=sha(REG/'selection_receipt.json'))),flush=True)

if __name__=='__main__':main()
