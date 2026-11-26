"""Independent read-only validation of the completed P1 run (writes receipts only)."""
import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import hypergeom,fisher_exact
from common import ROOT,OUT,CODE,DATA,Budget,load_data,fold_ids,verify_public_hashes,sha,dump,now


def main():
    before=Budget().count();d=load_data('02',True);ids=d.id.astype(str)
    indexed=d.assign(id=ids).set_index('id')
    freeze=json.loads((OUT/'experiment_freeze.json').read_text())
    assert freeze['public_hashes']==verify_public_hashes()
    for name,digest in freeze['core_code_hashes'].items():assert sha(CODE/name)==digest,name
    assert sha(ROOT/'codex/P1_PLANv2.md')==freeze['plan_sha256']
    preflight=json.loads((OUT/'preflight.json').read_text())
    for name,digest in preflight['feature_hashes'].items():assert sha(OUT/'features'/name)==digest
    splits=json.loads((OUT/'splits.json').read_text());checked=0
    elements=sorted(set(d.A)|set(d.B));blocks=fold_ids(elements,5,'elements')
    for name,s in splits.items():
        tr=indexed.loc[list(map(str,s['train']))];te=indexed.loc[list(map(str,s['test']))]
        assert not set(tr.index)&set(te.index)
        assert not set(tr.ab)&set(te.ab)
        if name.startswith('element_'):
            f=int(name.split('_')[-1]);held={x for x,k in zip(elements,blocks) if k==f}
            assert not (set(tr.A)|set(tr.B))&held
            assert (te.A.isin(held)|te.B.isin(held)).all()
        if name.startswith('xleave_'):
            x=name.split('_')[1];assert (tr.X!=x).all() and (te.X==x).all()
        if name.startswith('target_'):
            threshold=float(name.split('_')[-1]);assert (tr.V>=threshold).all()
        checked+=1
    ledger=Budget().entries();starts=[r for r in ledger if r['event']=='start'];finished=[r for r in ledger if r['event']=='finish'];failed=[r for r in ledger if r['event']=='failed']
    assert [r['fit_number'] for r in starts]==list(range(1,len(starts)+1))
    assert len(starts)==len(finished)+len(failed)<=1000
    trace_count=0
    for r in starts:
        if 'key' not in r or r['event']!='start':continue
        path=OUT/'models'/(r['key']+'.json')
        if not path.exists():assert any(f.get('key')==r['key'] for f in failed);continue
        meta=json.loads(path.read_text());train=set(meta['train_ids']);phase=r['phase']
        assert train<=set(ids),phase
        if phase in splits:allowed=set(map(str,splits[phase]['train']))
        elif phase.startswith(('feature_','ablation_','query_seed_')):
            f=phase.split('_')[-1];allowed=set(map(str,splits[f'main_outer_{f}']['train']))
        else:allowed=set(ids)
        assert train<=allowed,(phase,len(train-allowed))
        if meta['group_sizes'] is not None:
            assert sum(meta['group_sizes'])==meta['train_n']
            assert max(meta['group_sizes'])<=20000
            if meta['target']=='rank_single':assert len(meta['group_sizes'])==1
        trace_count+=1
    final=json.loads((OUT/'final_selection.json').read_text())
    assert len(final['candidates'])<=3
    for v in final['models'].values():
        meta=json.loads((OUT/'models'/(v['tree_key']+'.json')).read_text());assert set(meta['train_ids'])<=set(ids)
    weights=json.loads((OUT/'weights_freeze_pre04.json').read_text())
    assert weights['04_export_already_exists'] is False
    assert weights['time']<json.loads((OUT/'prediction_freeze.json').read_text())['time']
    for name,digest in weights['weights'].items():assert sha(OUT/'models'/name)==digest
    prediction_manifest=json.loads((OUT/'predictions/manifest.json').read_text())
    expected={'04':3703,'06':15225,'07':2704,'08':8112,'11':529,'12':1587}
    for prefix,n in expected.items():
        path=OUT/'predictions'/f'{prefix}_P1_train02_predictions.csv'
        frame=pd.read_csv(path,float_precision='round_trip');source=load_data(prefix)
        assert len(frame)==n and frame.key.is_unique
        assert set(frame.key)==set(source.key)
        assert (frame.model_scope=='P1_train02').all() and (frame.screen_event=='V<=2').all()
        assert np.isfinite(frame.vhat).all() and (frame.vhat>=0).all()
        assert sha(path)==prediction_manifest['files'][path.name]
        assert not {'V','gap','e_form','vbm','cbm'}&set(frame.columns)
        if final['screen'] in ('R-raw','R-log','W-log','H-soft'):
            np.testing.assert_allclose(frame.screen_score,-frame.vhat,atol=1e-12,rtol=1e-12)
    # Independent inference entry point reads only composition columns.
    replay=OUT/'audit_inference_replay.csv'
    command=['/usr/bin/python3.10',str(CODE/'predict.py'),'--input',str(next(DATA.glob('04_*.csv'))),'--output',str(replay)]
    proc=subprocess.run(command,capture_output=True,text=True,check=True)
    re=pd.read_csv(replay,float_precision='round_trip');official=pd.read_csv(OUT/'predictions/04_P1_train02_predictions.csv',float_precision='round_trip')
    np.testing.assert_allclose(re.vhat,official.vhat,rtol=1e-12,atol=1e-12)
    np.testing.assert_allclose(re.screen_score,official.screen_score,rtol=1e-12,atol=1e-12)
    # Independently verify the four literature CSV scenarios with exact integers.
    examples=[]
    for N,h in [(18928,2),(18928,3),(3703,2),(3703,3)]:
        M=19;k=20;den=math.comb(N,k)
        exact=float(sum((Fraction(math.comb(M,j)*math.comb(N-M,k-j),den) for j in range(h,min(M,k)+1)),Fraction()))
        scipy_p=float(hypergeom.sf(h-1,N,M,k))
        fisher_p=float(fisher_exact([[h,k-h],[M-h,N-M-k+h]],alternative='greater').pvalue)
        assert abs(exact-scipy_p)<1e-12 and abs(exact-fisher_p)<1e-12
        examples.append(dict(N=N,M=M,k=k,h=h,EF=(h/k)/(M/N),p=exact,role='hypothetical, not experiment result'))
    assert Budget().count()==before
    interface_manifest=json.loads((OUT/'interface/manifest.json').read_text())
    for rec in interface_manifest['tables']:
        path=OUT/'interface'/rec['file'];assert sha(path)==rec['sha256']
        with np.load(path,allow_pickle=False) as z:
            assert z['allowed'].dtype==np.bool_
            assert int(z['allowed'].sum())==rec['allowed_rows']
            assert np.isnan(z['vhat'][~z['allowed']]).all()
            assert np.isfinite(z['vhat'][z['allowed']]).all()
    top=pd.read_csv(OUT/'predictions/04_screen_top20.csv');assert len(top)==20
    main=pd.read_csv(OUT/'results/P1_final_experiment_table.csv')
    for r in main[main.RMSE.notna()].itertuples():assert np.isclose(r.RMSE**2,r.metal_MSE_contribution+r.nonmetal_MSE_contribution)
    receipt=dict(time=now(),passed=True,split_protocols_checked=checked,tree_lineages_checked=trace_count,
                 fits=before,failed_attempts=len(failed),independent_inference=True,no_training_in_audit=True,
                 example_statistics=examples,core_hashes_unchanged=True,final_weights_frozen_before_04=True,
                 outputs_match_pool_membership=True,explicit_interface_masks=True,feature_hashes_unchanged=True,
                 postprocessing_code_hashes={p.name:sha(p) for p in CODE.glob('*.py') if p.name not in freeze['core_code_hashes']})
    dump(OUT/'final_audit.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('example_statistics','postprocessing_code_hashes')},ensure_ascii=False))


if __name__=='__main__':main()
