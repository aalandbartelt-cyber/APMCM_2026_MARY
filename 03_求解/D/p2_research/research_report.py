"""Read-only aggregation of research outcomes; no solver or model imports."""
from pathlib import Path
import csv, hashlib, json, math
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'artifacts/p2_research_20261128'

def read(p):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]

def stats(name, rows):
    valid=[r for r in rows if r['status']=='VALID_COMPLETED']
    usable=[r for r in valid if r.get('regret') is not None]
    strict=[r for r in usable if r.get('all_chains_feasible',r.get('feasible',False))]
    n=len(rows)
    d=dict(setting=name,attempts=n,valid=len(valid),failures=n-len(valid),
           strict_feasible=len(strict),usable=len(usable),
           optimal=sum(r['regret']==0 for r in usable),
           strict_optimal=sum(r['regret']==0 for r in strict),
           regret_le_01=sum(r['regret']<=.1 for r in usable),
           strict_regret_le_01=sum(r['regret']<=.1 for r in strict),
           regret_le_2=sum(r['regret']<=2 for r in usable),
           strict_regret_le_2=sum(r['regret']<=2 for r in strict))
    ranks=[r.get('rank',1 if r['regret']==0 else None) for r in usable]
    for k in [1,5,10,20,50,100]:
        d[f'top{k}']=sum(r<=k for r in ranks) if all(r is not None for r in ranks) else None
        sranks=[r.get('rank',1 if r['regret']==0 else None) for r in strict]
        d[f'strict_top{k}']=sum(r<=k for r in sranks) if all(r is not None for r in sranks) else None
    ranks=[r for r in ranks if r is not None]
    d['median_rank_conditional_usable']=float(np.median(ranks)) if ranks else None
    sranks=[r for r in sranks if r is not None]
    d['median_rank_conditional_strict']=float(np.median(sranks)) if sranks else None
    for subset,label in [(usable,'usable'),(strict,'strict')]:
        vals=[r['regret'] for r in subset]
        for pct in [0,50,90,95,100]:
            d[f'regret_q{pct}_conditional_{label}']=float(np.percentile(vals,pct)) if vals else None
    for key in ['strict_feasible','usable','optimal','strict_optimal','regret_le_2']:
        d[key+'_per_attempt']=d[key]/n if n else None
    p=d['optimal']/n if n else 0
    d['R99_plugin_usable']=1 if p==1 else math.ceil(math.log(.01)/math.log1p(-p)) if p>0 else None
    ps=d['strict_optimal']/n if n else 0
    d['R99_plugin_strict']=1 if ps==1 else math.ceil(math.log(.01)/math.log1p(-ps)) if ps>0 else None
    d['strict_feasible_per_valid_return']=len(strict)/len(valid) if valid else None
    d['strict_optimal_per_strict_feasible']=d['strict_optimal']/len(strict) if strict else None
    d['R99_assumption']='IID constant per-attempt probability; descriptive plug-in, not CIM TTS'
    return d

def write_csv(p, rows):
    with p.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    out=BASE/'final_summary';out.mkdir(exist_ok=False)
    groups=[];raw_files=[]
    for p in sorted(BASE.rglob('raw.jsonl')):
        if out in p.parents:continue
        rows=read(p)
        if not rows:continue
        groups.append(stats(str(p.parent.relative_to(BASE)),rows));raw_files.append(p)
    write_csv(out/'all_blocks.csv',groups)
    vroot=BASE/'validation_H07_H08'
    reg=json.loads((vroot/'registration.json').read_text())
    assert len(reg['specs'])==23
    for s in reg['specs']:
        assert (vroot/s['name']/'summary.json').exists()
        assert len(read(vroot/s['name']/'raw.jsonl'))==100
        assert hashlib.sha256((vroot/s['name']/'matrix.npz').read_bytes()).hexdigest()==reg['matrix_files_sha256'][s['name']]
    pooled=[]
    for kind in ['real','zero']:
        rows=sum([read(vroot/f'blind_{kind}_{i:02d}'/'raw.jsonl') for i in range(5)],[])
        pooled.append(stats(f'H07_blind_{kind}_500',rows))
    merged=[]
    for kind in ['real','zero']:
        batches=[read(vroot/f'full_batch{i}_{kind}'/'raw.jsonl') for i in range(5)]
        z=np.load(vroot/f'full_batch0_{kind}'/'matrix.npz');q=z['q'];v=z['values']
        rows=[]
        for i in range(100):
            block=[b[i] for b in batches];assert all(r['index']==i for r in block)
            ok=[r for r in block if r['status']=='VALID_COMPLETED' and r.get('candidate') is not None]
            c=min([r['candidate'] for r in ok],key=lambda c:(q[c],c)) if ok else None
            complete=all(r['status']=='VALID_COMPLETED' for r in block)
            # Main merged result requires all five returns to pass integrity.
            row=dict(index=i,status='VALID_COMPLETED' if complete else 'FAILED',
                all_chains_feasible=complete and all(r.get('all_chains_feasible',False) for r in block),
                candidate=c if complete else None,regret=float(v[c]-v.min()) if complete and c is not None else None,
                rank=int(1+sum(v<v[c])) if complete and c is not None else None,
                component_valid_returns=sum(r['status']=='VALID_COMPLETED' for r in block),
                partial_candidate=c,partial_regret=float(v[c]-v.min()) if c is not None else None)
            rows.append(row)
        (out/f'full_merged_{kind}.json').write_text(json.dumps(rows,indent=2))
        d=stats(f'H08_full_{kind}_100_five_call_units',rows)
        merged.append(d)
    write_csv(out/'validation_pooled.csv',pooled+merged)
    # Whole-pool representation certificate, independently derived from final q and mappings.
    z=np.load(vroot/'full_batch0_real/matrix.npz');q=z['q'];v=z['values']
    maps=[]
    cert=json.loads((vroot/'independent_full_audit.json').read_text())['matrices']
    for i in range(5):
        assert cert[f'full_batch{i}_real']['G1']=='CERTIFIED'
        maps += sum([b['mapping'] for b in json.loads((vroot/f'full_batch{i}_real/blocks.json').read_text())],[])
    assert maps==list(range(2704))
    c=np.flatnonzero(q==q.min());worst=float((v[c]-v.min()).max())
    assert worst<=.1
    (out/'full_merged_certificate.json').write_text(json.dumps(dict(
        G1='CERTIFIED',G2='CERTIFIED',all_candidates_covered_once=len(maps),
        global_min_q_candidates=c.tolist(),worst_original_regret=worst,
        contract='All five independently certified real matrices at ground state; choose minimum(q,index) across every chain. Not a certificate of sampled states.'),indent=2))
    total=sum(g['attempts'] for g in groups);valid=sum(g['valid'] for g in groups)
    # Twenty tiny SDK repeat-seed probes live outside raw.jsonl format.
    (out/'ledger.json').write_text(json.dumps(dict(raw_jsonl_attempts=total,
        raw_jsonl_valid=valid,raw_jsonl_failures=total-valid,
        separate_repeat_seed_probes=20,total_SA_calls_or_attempt_slots=total+20,
        old_SA_excluded=40000,new_CIM_submissions=0,new_fits=0,
        pre_SA_initialization_failures_H04=6,
        note='All failures retained; H04 six pre-SA failures later performed first samples in fresh processes; do not double-count them as 600 sampled returns.',
        raw_file_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in raw_files}),indent=2))
    print(json.dumps(dict(pooled=pooled,full_merged=merged,total_raw_attempts=total,valid=valid),indent=2))

if __name__=='__main__':main()
