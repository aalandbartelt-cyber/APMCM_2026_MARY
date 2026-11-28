"""Check derived margins, chain nesting, SA prefix counts and the protected hashes."""
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'figures/P2/data'
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for buf in iter(lambda:f.read(1048576),b''):h.update(buf)
    return h.hexdigest()
def read(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))
def groups(rows,*keys):
    out=defaultdict(list)
    for r in rows:out[tuple(r[k] for k in keys)].append(r)
    return out
def check(ok,reason):
    if not ok:raise ValueError(reason)
def verify_seals():
    files={}
    for f,key in [('codex/p2_dual_rescue/registration.json','protected'),('codex/p2_research_receipt/receipt.json','files'),('codex/p2_cim_service/final_seal.json','files')]:
        orig=json.loads((ROOT/f).read_text())[key]
        failed=[name for name,expected in orig.items() if not (ROOT/name).is_file() or digest(ROOT/name)!=expected]
        check(not failed, f+': '+str(failed[:4]))
        files[f]=len(orig)
    return files
def compare_certificates():
    oldroot=ROOT/'artifacts/p2_research_20261128'
    errata=json.loads((oldroot/'zero_control_certificate_erratum.json').read_text())['corrections']
    matched={}
    for tag,folder in [('h05','short_H05'),('final','validation_H07_H08')]:
        old=json.loads((oldroot/folder/'independent_full_audit.json').read_text())
        new=json.loads((ROOT/'codex/p2_zero'/('replay_'+tag+'.json')).read_text())
        check(old['matrices'].keys()==new['matrices'].keys(),'matrix list')
        for arm,baseline in old['matrices'].items():
            expected={**baseline,**errata[folder].get(arm,{})}
            for key,value in expected.items():
                if key!='mapped_candidates':check(new['matrices'][arm].get(key)==value,arm+' '+key)
        matched[tag]=len(old['matrices'])
    return matched

def verify_figures():
    for m in read(DATA/'figure_data_manifest.csv'):
        p=ROOT/m['file']
        check(digest(p)==m['sha256'] and digest(ROOT/m['generator'])==m['generator_sha256'],m['file'])
        for f,h in zip(m['sources'].split(';'),m['source_sha256'].split(';')):check(digest(ROOT/f)==h,f)
    for f in ['sa_sources.json','timing_sources.json']:
        m=json.loads((DATA/f).read_text())
        source=m.items() if isinstance(m,dict) else [(x['source_path'],x['sha256']) for x in m]
        for p,h in source:check(digest(ROOT/p)==h,p)
    margin=read(DATA/'task_margin.csv');energy=read(DATA/'return_energy.csv');detail=read(DATA/'chain_detail.csv')
    check((len(margin),len(energy),len(detail))==(25,250,10000),'shape')
    by_task=groups(energy,'slot');by_vector=groups(detail,'slot','return_index')
    wide={r['slot']:r for r in read(DATA/'chain_task_25x40.csv')}
    for t in margin:
        es=by_task[t['slot'],]
        rr=[int(r['residual']) for r in es]
        check(196-max(rr)==int(t['set_min_margin']) and 196-min(rr)==int(t['selected_margin']),t['slot'])
        all_counts=Counter()
        for e in es:
            chains=by_vector[e['slot'],e['return_index']]
            check(len(chains)==40 and 4*sum(int(r['q_excess']) for r in chains)==int(e['residual']),'energy decomposition')
            check(sum(int(r['optimal']) for r in chains)==int(e['locally_optimal_chains']),'local minima')
            all_counts.update(int(r['chain']) for r in chains if int(r['optimal']))
        check(all(all_counts[b]==int(wide[t['slot']][f'chain_{b:02}']) for b in range(1,41)),'task heatmap')
    attempts=read(DATA/'sa_attempts.csv');blocks=read(DATA/'sa_budget_blocks.csv');curves=read(DATA/'sa_budget_curve.csv')
    check(len(attempts)==5200 and len(blocks)==364 and len(curves)==49,'SA grid coverage')
    slots=read(ROOT/'codex/p2_zero/slots.csv')
    fresh_slots={(r['arm'],r['block'],r['index'],r['seed']) for r in attempts if r['source']=='fresh'}
    check(len(fresh_slots)==4200 and fresh_slots=={(r['arm'],r['block'],r['index'],r['seed']) for r in slots},'registered slots')
    br=groups(attempts,'source','arm','block')
    for b in blocks:
        rr=sorted(br[b['source'],b['arm'],b['block']],key=lambda x:int(x['index']))[:int(b['budget'])]
        strict=[r for r in rr if r['strict']=='1'];winner=min(strict,key=lambda r:(int(r['energy']),int(r['index']))) if strict else None
        check(any(r['hit']=='1' for r in rr)==bool(int(b['any_hit'])) and (winner['hit'] if winner else '0')==b['energy_hit'],'SA prefix')
    for c in curves:
        rr=[b for b in blocks if b['arm']==c['arm'] and b['budget']==c['budget'] and b['source']==c['source'].split('_')[0] and (c['source']!='fresh_length_paired' or int(b['block'])<2)]
        check(len(rr)==int(c['planned_blocks']) and sum(int(b['any_hit']) for b in rr)==int(c['strict_hit_blocks']) and sum(int(b['energy_hit']) for b in rr)==int(c['energy_hit_blocks']),'curve')
    test=json.loads((DATA/'sa_paired_test.json').read_text())
    primary={a:{b['block']:b['any_hit'] for b in blocks if b['source']=='fresh' and b['budget']=='5' and b['arm']==a} for a in test['arms']}
    a,b=primary.values()
    counts=Counter(a[j]+b[j] for j in a);check(all(n==counts[k] for k,n in test['table'].items()),'paired table')
    if test['complete']:
        n=counts['10']+counts['01']
        # Compute two-sided tail by enumerating both symmetric tails.
        k=min(counts['10'],counts['01'])
        num=sum(math.comb(n,i) for i in range(n+1) if min(i,n-i)<=k)
        check(num/(2**n)==test['p_two_sided'],'exact test')
    return dict(tasks=len(margin),vectors=len(energy),chain_choices=len(detail),sa_slots=len(attempts),registered_fresh_slots=len(fresh_slots),budget_curve_rows=len(curves),manifest_files=len(read(DATA/'figure_data_manifest.csv')))
if __name__=='__main__':
    results={'protected_counts':verify_seals()}
    if '--seals-only' not in sys.argv:
        results['certificates_match_corrected_archive']=compare_certificates()
        results['crosschecks']=verify_figures()
        from check_sa_export import replay
        import contextlib,io
        buffer=io.StringIO()
        with contextlib.redirect_stdout(buffer):replay()
        results['portable_sa_replay']=buffer.getvalue().strip()
    print(json.dumps(results,indent=2))
