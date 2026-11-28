"""Independent read-only replay of archived spins and frozen selection rules."""
from pathlib import Path
import hashlib,json,subprocess
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artifacts/p2_dual_rescue'
REG=ROOT/'codex/p2_dual_rescue'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
tie=lambda s:hashlib.sha256(('P1v2.1/tie/'+str(s)).encode()).hexdigest()

def main():
    registration=read(REG/'registration.json')
    for name,h in {**registration['protected'],**registration['input_hashes'],**registration['code_hashes']}.items():
        assert sha(ROOT/name)==h,name
    assert sha(registration['environment']['mutate_binary_path'])==registration['environment']['mutate_binary_sha256']
    A=read(REG/'A_receipt.json');manifest=read(REG/'B_manifest.json');B=read(REG/'B_receipt.json')
    assert A['selected'] is None and not A['B_extra_candidates']
    assert len(A['candidates'])==2 and len(manifest['candidates'])==8
    assert sha(ROOT/manifest['code_file'])==manifest['code_sha256']
    total=0;witnesses=0;mutate_matches={};summary=[]
    for row in A['candidates']:
        directory=OUT/'mutate'/row['id'];receipt=read(directory/'first_output_receipt.json')
        assert receipt['top_level_calls']==1 and sha(ROOT/receipt['file'])==receipt['sha256']
        assert (directory/'call_started.json').is_file() and not (directory/'error.json').exists()
        assert read(directory/'process_closeout.json')['exit_code']==0
        enc='raw' if 'raw' in row['id'] else 'rc'
        J=np.load(ROOT/receipt['file']);expected=np.rint(J*127/np.abs(J).max()).astype(np.int64)
        K=np.load(ROOT/row['matrix_file'])['J'];np.testing.assert_array_equal(K,expected)
        old=np.load(ROOT/f'artifacts/p2_rescue1/representations/11-{enc}-N8-rescue1.npz')['J']
        mutate_matches[row['id']]=bool(np.array_equal(K,old))
    for row in [*A['candidates'],*manifest['candidates']]:
        assert sha(ROOT/row['matrix_file'])==row['matrix_sha256']
        z=np.load(ROOT/row['matrix_file']);K=z['J'];mask=z['allowed'];W=z['W']
        assert K.dtype.kind in 'iu' and K.shape==(105,105) and np.array_equal(K,K.T)
        X=np.zeros((2704,104),np.int64)
        for i in range(52):
            for j in range(52):X[i*52+j,i]=X[i*52+j,52+j]=1
        S=np.c_[2*X-1,np.ones(2704,np.int64)];E=-np.sum((S@K)*S,axis=1).reshape(52,52)
        opt=E[mask].min();regret=W[(E==opt)&mask].max()-W[mask].min()
        assert abs(regret-row['worst_ground_regret'])<1e-12
        cert=read((ROOT/row['matrix_file']).with_suffix('.certificate.json'))
        if cert['status']=='COUNTEREXAMPLE':
            x=np.asarray(cert['witness']);s=np.r_[2*x-1,1]
            assert -s@K@s==cert['witness_energy']<=opt
            ac=x[:52].sum();bc=x[52:].sum()
            assert (ac,bc)!=(1,1) or not mask[x[:52].argmax(),x[52:].argmax()]
            witnesses+=1
        if row['id'].startswith('A-'):continue
        J=np.load(OUT/'inputs'/f'{row["id"]}_real_J.npy')
        np.testing.assert_array_equal(K,np.rint(J*(127/np.abs(J).max())).astype(np.int64))
        assert row['meta']['max_abs_J']==float(np.abs(J).max())
        block_regrets=[];feasible_count=0;valid_count=0;success=0;oracle=0
        for block in range(10):
            data=read(OUT/'SA_B'/row['id']/f'block_{block:02}.json');assert len(data['restarts'])==100
            candidates=[]
            for index,item in enumerate(data['restarts']):
                total+=1;assert item['seed']==230026+100*block+index
                if item['status']!='VALID_COMPLETED':continue
                valid_count+=1;s=np.asarray(item['spins'],np.int64)
                assert s.shape==(105,) and np.isin(s,[-1,1]).all()
                x=(s[:-1]*s[-1]+1)//2;ac=int(x[:52].sum());bc=int(x[52:].sum())
                i=int(x[:52].argmax());j=int(x[52:].argmax());f=ac==1 and bc==1 and bool(mask[i,j])
                assert f==item['feasible'];assert int(-s@K@s)==item['energy']
                if f:
                    feasible_count+=1;reg=float(W[i,j]-W[mask].min());assert abs(reg-item['regret'])<1e-12
                    candidates.append((item['energy'],tie(item['key']),index,reg))
                else:assert item['regret'] is None
            chosen=min(candidates) if candidates else None
            assert data['selected_restart']==(chosen[2] if chosen else None)
            r=chosen[3] if chosen else float('inf');block_regrets.append(r)
            if chosen:assert abs(data['selected_regret']-r)<1e-12
            else:assert data['selected_regret'] is None
            success+=r<=2;oracle+=any(x[3]<=2 for x in candidates)
        sorted_r=sorted(block_regrets);median=(sorted_r[4]+sorted_r[5])/2
        summary.append(dict(id=row['id'],valid_returns=valid_count,feasible_raw=feasible_count,
            selected_block_successes=int(success),oracle_block_success_rate=oracle/10,
            block_regret_median=median,eligible=feasible_count>100 and median<=2))
    table=pd.read_csv(OUT/'results/B_full_grid.csv').set_index('id')
    for s in summary:
        for key in ['valid_returns','feasible_raw','selected_block_successes','oracle_block_success_rate','block_regret_median','eligible']:
            assert table.loc[s['id'],key]==s[key],(s['id'],key)
    qualified=sorted([s for s in summary if s['eligible']],key=lambda s:(-s['feasible_raw'],s['id']))
    assert B['selected']==(qualified[0]['id'] if qualified else None)
    assert sha(OUT/'results/B_full_grid.csv')==B['results_sha256']
    return dict(protected_files=len(registration['protected']),mutate_top_level_calls=2,
        mutate_quantized_equal_rescue1=mutate_matches,all_onehot_energies_checked=27040,
        integer_witnesses_checked=witnesses,raw_SA_restarts_checked=total,blocks_checked=80,
        independent_selection=B['selected'],new_model_fits=0,manuscript_hashes_unchanged=True)

if __name__=='__main__':print(json.dumps(main(),indent=2))
