"""Replay every available attempt; export plan denominators and paired-block inference."""
import csv, hashlib,json,math
from collections import Counter
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'figures/P2/data'
BASE=ROOT/'artifacts/p2_research_20261128'
OUT=ROOT/'artifacts/p2_zero'
REG=ROOT/'codex/p2_zero'
BUDGETS=[1,2,5,10,20,50,100]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def read_series(arm,block,source,rows_path,params_path,expected_seed,inputs):
    z=np.load(params_path/'matrix.npz');K=z['J'];q=z['q'];v=z['values']
    blocks=json.loads((params_path/'blocks.json').read_text())
    inputs.update({str(f.relative_to(ROOT)):sha(f) for f in [params_path/'matrix.npz',params_path/'blocks.json']})
    raw=[]
    if rows_path.exists():
        inputs[str(rows_path.relative_to(ROOT))]=sha(rows_path)
        raw=[json.loads(l) for l in rows_path.read_text().splitlines()]
    assert len(raw)<=100 and [r['index'] for r in raw]==list(range(len(raw)))
    ii,jj=np.nonzero(np.triu(K,1));weights=-2*K[ii,jj]
    result=[]
    for i in range(100):
        seed=expected_seed+i
        data=dict(source=source,arm=arm,block=block,index=i,seed=seed,status='NOT_STARTED',strict=0,hit=0,partial=0,original_regret='NA',energy='NA',candidate='NA',spins=len(K),bits_hex='',failure='NA')
        if i<len(raw):
            r=raw[i];assert r['seed']==seed
            data['status']=r['status']
            if r['status']=='VALID_COMPLETED':
                s=np.array(r['spins'],dtype=np.int64) if 'spins' in r else (2*np.unpackbits(np.frombuffer(bytes.fromhex(r['bits']),dtype='uint8'))[:len(K)].astype(np.int64)-1)
                assert len(s)==len(K) and np.isin(s,[-1,1]).all()
                e=int(sum(weights*s[ii]*s[jj])); choices=[]
                for b in blocks:
                    d=s[b['start']:b['stop']]*s[-1]
                    if np.all(d[:-1]>=d[1:]):choices.append(b['mapping'][np.count_nonzero(d==1)])
                c=min(choices,key=lambda x:(q[x],x)) if choices else None
                strict=len(choices)==len(blocks);regret=float(v[c]-min(v)) if c is not None else None
                assert e==r['energy'] and strict==r['all_chains_feasible'] and c==r['candidate'] and regret==r['regret']
                data.update(strict=int(strict),hit=int(strict and regret==0),partial=int(bool(choices)),original_regret='NA' if regret is None else regret,energy=e,candidate='NA' if c is None else c,bits_hex=np.packbits(s>0).tobytes().hex())
            else:data['failure']=r.get('error','FAILED').split(':',1)[0]
        result.append(data)
    return result
def summarize(rows,b):
    part=rows[:b];r=part[0]
    strict=[x for x in part if x['strict']]; chosen=min(strict,key=lambda x:(x['energy'],x['index'])) if strict else None
    hits=[x for x in part if x['hit']]
    return dict(source=r['source'],arm=r['arm'],block=r['block'],budget=b,attempted=sum(x['status']!='NOT_STARTED' for x in part),valid=sum(x['status']=='VALID_COMPLETED' for x in part),failed=sum(x['status'] not in ('NOT_STARTED','VALID_COMPLETED') for x in part),strict_returns=len(strict),any_strict=int(bool(strict)),any_hit=int(bool(hits)),first_hit_slot=1+hits[0]['index'] if hits else 'NA',best_regret=min((x['original_regret'] for x in strict),default='NA'),energy_hit=chosen['hit'] if chosen else 0,energy_regret=chosen['original_regret'] if chosen else 'NA')
def exact(n10,n01):
    n=n10+n01
    return min(1,2*sum(math.comb(n,i) for i in range(min(n10,n01)+1))/(2**n))
def main():
    reg=json.loads((REG/'registration.json').read_text())
    assert all(sha(ROOT/k)==h for k,h in reg['hashes'].items())
    attempts=[];blocks=[];inputs={};ablation=[]
    for source,number in [('H07',5),('fresh',20)]:
        for j in range(number):
            for arm in (['40_real','40_zero','single_real'] if source=='fresh' and j<2 else ['40_real','40_zero']):
                pp=OUT/'single_real' if arm=='single_real' else BASE/'short_H05'/arm
                raw=OUT/f'{arm}_{j:02}.jsonl' if source=='fresh' else BASE/'validation_H07_H08'/f"blind_{arm.split('_')[1]}_{j:02}"/'raw.jsonl'
                rows=read_series(arm,j,source,raw,pp,(710001 if source=='fresh' else 360001)+100*j,inputs);attempts+=rows
                blocks.extend(summarize(rows,b) for b in BUDGETS)
    write(DATA/'sa_attempts.csv',attempts)
    write(DATA/'sa_budget_blocks.csv',blocks)
    curves=[]
    for source in ('H07','fresh','fresh_length_paired'):
        for arm in (['40_real','single_real'] if source.endswith('paired') else ['40_real','40_zero']+(['single_real'] if source=='fresh' else [])):
            for b in BUDGETS:
                rr=[r for r in blocks if r['source']==source.split('_')[0] and r['arm']==arm and r['budget']==b and (not source.endswith('paired') or r['block']<2)]
                if not rr:continue
                w=len(rr);hit=sum(r['any_hit'] for r in rr);eh=sum(r['energy_hit'] for r in rr)
                curves.append(dict(source=source,arm=arm,chains=1 if arm=='single_real' else 40,budget=b,planned_blocks=w,complete_blocks=sum(r['attempted']==b for r in rr),attempted_slots=sum(r['attempted'] for r in rr),failed_slots=sum(r['failed'] for r in rr),strict_hit_blocks=hit,strict_hit_fraction=hit/w,energy_hit_blocks=eh,energy_hit_fraction=eh/w,no_strict_blocks=sum(1-r['any_strict'] for r in rr),best_regret_median_conditional=median_or_na([r['best_regret'] for r in rr]),energy_regret_median_conditional=median_or_na([r['energy_regret'] for r in rr])))
    write(DATA/'sa_budget_curve.csv',curves)
    vs=[{r['block']:r for r in blocks if r['source']=='fresh' and r['arm']==arm and r['budget']==5} for arm in ('40_real','40_zero')]
    tab=Counter((vs[0][j]['any_hit'],vs[1][j]['any_hit']) for j in range(20))
    complete=all(r['attempted']==100 for r in blocks if r['source']=='fresh' and r['budget']==100)
    test=dict(endpoint='at least one strict original optimum in first five attempts',unit='paired 100-attempt block; one five-attempt prefix per block',n=20,arms=['40_real','40_zero'],classification='prospectively registered local test conditional on selected matrix and seed protocol',alpha=.05,table={f'{a}{b}':tab[a,b] for a in (1,0) for b in (1,0)},delta=(tab[1,0]-tab[0,1])/20,complete=complete,p_two_sided=exact(tab[1,0],tab[0,1]) if complete else None,assumptions='Independent seed-block pairs; under equal marginal hit probabilities each discordance sign is equiprobable. Inference conditional on seed design.')
    (DATA/'sa_paired_test.json').write_text(json.dumps(test,indent=2)+'\n')
    def abl(name,arm,rs,n,groups,shape,Q,P,T,scale_hash,source_path):
        ok=[r for r in rs if r.get('strict')];hits=[r for r in ok if r['original_regret']==0]
        if name=='H02':
            certpath=BASE/'shaping_H02/post_sampling_audit.json'
            entry=json.loads(certpath.read_text())[arm]
            g1=g2=entry['status']
            gap=entry['illegal_gap']; ground=entry['global_legal_min']
        else:
            certpath=REG/('single_certificate.json' if arm=='single_real' else 'replay_h05.json')
            entry=json.loads(certpath.read_text())
            if arm!='single_real':entry=entry['matrices'][arm]
            g1=entry['G1'];g2=entry['G2'];gap=entry['illegal_gap'];ground=entry['ground_energy']
        inputs[str(certpath.relative_to(ROOT))]=sha(certpath)
        ablation.append(dict(G1=g1,G2=g2,illegal_gap=gap,ground_energy=ground,cohort=name,arm=arm,planned=len(rs),attempted=sum(r['status']!='NOT_STARTED' for r in rs),valid=sum(r['status']=='VALID_COMPLETED' for r in rs),strict=len(ok),strict_hits=len(hits),conditional_median_regret=median_or_na([r['original_regret'] for r in ok]),spins=n,chains=groups,shape=shape,q_upper=Q,penalty=P,T_initial=T,iterations_per_temperature=550,max_candidates_per_vector=groups,max_classical_min_comparisons=groups-1,coefficient_max=int(abs(np.load(source_path/'matrix.npz')['J']).max()),matrix_hash=scale_hash,certificate_source=('codex/p2_zero/single_certificate.json' if arm=='single_real' else 'codex/p2_zero/replay_h05.json') if Q==63 else 'artifacts/p2_research_20261128/shaping_H02/post_sampling_audit.json'))
    for source,arms in [('H02',['single_linear','packed_linear','packed_piecewise2']),('H05',['20_real','20_zero','40_real','40_zero'])]:
        for arm in arms:
            pp=BASE/('shaping_H02' if source=='H02' else 'short_H05')/arm
            records=[json.loads(l) for l in (pp/'raw.jsonl').read_text().splitlines()]
            for fp in [pp/'raw.jsonl',pp/'matrix.npz',pp/'blocks.json',pp.parent/'registration.json']+([pp/'settings.json'] if (pp/'settings.json').is_file() else []):
                inputs[str(fp.relative_to(ROOT))]=sha(fp)
            rs=[dict(status=r['status'],strict=r.get('all_chains_feasible',False),original_regret=r.get('regret')) for r in records];z=np.load(pp/'matrix.npz');K=z['J'];g=len(json.loads((pp/'blocks.json').read_text()))
            t=4*np.abs(K).sum(1).max() if source=='H02' else json.loads((pp/'settings.json').read_text())['scale']
            abl(source,arm,rs,len(K),g,'linear' if 'linear' in arm else ('zero cost; real-q decoder' if 'zero' in arm else 'piecewise2'),127 if source=='H02' else 63,254 if source=='H02' else 128,t,sha(pp/'matrix.npz'),pp)
    for arm in ['single_real','40_real']:
        rs=[r for r in attempts if r['source']=='fresh' and r['arm']==arm and r['block']<2]
        pp=OUT/arm if arm=='single_real' else BASE/'short_H05'/arm
        abl('fresh_matched_2',arm,rs,rs[0]['spins'],1 if arm=='single_real' else 40,'piecewise2',63,128,26284,sha(pp/'matrix.npz'),pp)
    write(DATA/'chain_ablation.csv',ablation)
    (DATA/'sa_sources.json').write_text(json.dumps(inputs,indent=2)+'\n')
    print(json.dumps(test))
def median_or_na(values):
    x=[v for v in values if v not in (None,'NA')]
    return float(np.median(x)) if x else 'NA'
if __name__=='__main__':main()
