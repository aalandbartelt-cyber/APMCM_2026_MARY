"""Export local, task-clustered hardware diagnostics from the verified package."""
import csv,json,sys
from pathlib import Path
from collections import Counter
from statistics import median, mean
from math import sqrt
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'evidence/p2'))
from verify import read_model, spins, decode, read_csv, verify, HERE, digest
DATA=ROOT/'figures/P2/data'; LIVE=ROOT/'artifacts/p2_cim_go_20261128/live'
def save(name,rows):
    with (DATA/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
def tied_ranks(values):
    order=sorted(range(len(values)),key=values.__getitem__)
    ranks=[0.0]*len(order)
    i=0
    while i<len(order):
        j=i+1
        while j<len(order) and values[order[j]]==values[order[i]]:j+=1
        for ix in order[i:j]:ranks[ix]=(i+j-1)/2
        i=j
    return ranks

def rank_correlation(x,y):
    a,b=tied_ranks(x),tied_ranks(y)
    ma,mb=mean(a),mean(b)
    denom=sqrt(sum((v-ma)**2 for v in a)*sum((v-mb)**2 for v in b))
    return sum((v-ma)*(w-mb) for v,w in zip(a,b))/denom if denom else 'NA'

def describe_positions(rows,margins):
    output=[]
    for t in margins:
        rr=[r for r in rows if r['slot']==t['slot']]
        positive=[r for r in rr if r['q_excess']>0]
        all_ids=Counter(r['candidate'] for r in positive)
        count=max(all_ids.values(),default=0)
        ids=sorted(c for c,k in all_ids.items() if k==count)
        output.append(dict(slot=t['slot'],stage=t['stage'],chain_choices=len(rr),
            positive_excess_choices=len(positive),distinct_positive_candidates=len(all_ids),
            most_frequent_suboptimal_ids=','.join(map(str,ids)),max_identity_count=count,
            position_excess_rho=rank_correlation([r['relative_position'] for r in rr],[r['q_excess'] for r in rr]),
            position_excess_rho_positive=rank_correlation([r['relative_position'] for r in positive],[r['q_excess'] for r in positive]) if positive else 'NA',
            critical_optima=sum(r['critical']*r['optimal'] for r in rr)))
    save('chain_association.csv',output)

def main():
    verify();model=read_model(HERE);blocks,q,v,dictionary,_,minimum=model
    detail=[];energy=[];margin=[];matrix=[];task_counts=[];times=[];sources=[]
    for task in read_csv(HERE/'tasks.csv'):
        slot=task['slot'];base=dict(slot=slot,stage=task['stage']);ev=[];ct=[0]*40
        p=HERE/'returns'/f'{slot}.pkl'
        for idx,s in enumerate(spins(p)):
            choices,bad,e,c=decode(s,model);flags=[];d=e+58722
            assert c is not None and not any(bad)
            for b,(item,g,lo) in enumerate(zip(choices,blocks,minimum)):
                pos=g['mapping'].index(item);m=len(g['mapping'])
                extra=q[item]-lo;opt=int(extra==0);flags.append(opt);ct[b]+=opt
                detail.append(dict(**base,return_index=idx,chain=b+1,group_size=m,position=pos,relative_position=pos/(m-1),candidate=item,A=dictionary[item]['A'],B=dictionary[item]['B'],X=dictionary[item]['X'],q=q[item],q_min=lo,q_excess=extra,legal=int(bad[b]==0),optimal=opt,critical=int(226 in g['mapping'])))
            matrix.append(dict(**base,return_index=idx,**{f'chain_{b+1:02}':x for b,x in enumerate(flags)}))
            ev.append(dict(**base,return_index=idx,energy=e,residual=d,margin=196-d,strict=1,original_regret=v[c]-min(v),candidate=c,locally_optimal_chains=sum(flags),energy_selected=0))
        sel=min(ev,key=lambda r:(r['energy'],r['return_index']));sel['energy_selected']=1;energy+=ev
        dmin=min(x['residual'] for x in ev);dmax=max(x['residual'] for x in ev)
        margin.append(dict(**base,result_id=task['result_id'],returns=len(ev),strict_count=len(ev),energy_selected_index=sel['return_index'],min_energy=sel['energy'],min_residual=dmin,max_residual=dmax,selected_margin=196-dmin,set_min_margin=196-dmax,best_regret=min(x['original_regret'] for x in ev),energy_selected_regret=sel['original_regret']))
        task_counts.append(dict(**base,returns=len(ev),**{f'chain_{b+1:02}':n for b,n in enumerate(ct)}))
        root=LIVE/slot;file=root/'events.jsonl';events=[json.loads(l) for l in file.read_text().splitlines()]
        creates=[r for r in events if r.get('method')=='POST' and r.get('path','').endswith('/create_sdk_task/') and r.get('http_status')==200];assert len(creates)==1
        # Bind the create acknowledgement to the actual server-ID, not an intent timestamp.
        ack=list(root.glob(f"submit_*/{creates[0]['request_number']:03}_response.bin"));assert len(ack)==1
        assert json.loads(ack[0].read_bytes())['data']['result_id']==task['result_id']
        done=None
        for f in sorted(root.glob('poll_*/sdk_return.json')):
            o=json.loads(f.read_text());remote=o.get('data') or {}
            if o.get('code')=='0' and str(remote.get('code'))=='1000':
                done=f.parent/'safe_summary.json';break
        t0=creates[0]['completed_at'];t1=json.loads(done.read_text())['finished_at'] if done else None
        if t1:assert datetime.fromisoformat(t1)>=datetime.fromisoformat(t0)
        times.append(dict(**base,result_id=task['result_id'],accepted_at_local=t0,terminal_observed_at_local=t1 or 'NA',timezone='Asia/Shanghai',physical_start='NA',physical_end='NA',missing_reason='provider execution timestamps unavailable'+('' if t1 else '; terminal observation timestamp unavailable')))
        for f in [file,ack[0]]+([done,done.parent/'sdk_return.json'] if done else []):
            sources.append({'slot':slot,'source_path':str(f.relative_to(ROOT)),'sha256':digest(f)})
    for name,rows in [('task_margin',margin),('return_energy',energy),('chain_detail',detail),('chain_optimal_250x40',matrix),('chain_task_25x40',task_counts),('task_timeline',times)]:save(name+'.csv',rows)
    assert len(detail)==10000 and len(matrix)==len(energy)==250 and len(task_counts)==len(times)==25
    (DATA/'timing_sources.json').write_text(json.dumps(sources,indent=2)+'\n')
    chain_summary=[]
    for stage in ('pilot','formal'):
        group=[r for r in task_counts if r['stage']==stage]
        for i,b in enumerate(blocks,1):
            counts=[r[f'chain_{i:02}'] for r in group]
            pops=[r['returns'] for r in group]
            chain_summary.append(dict(stage=stage,chain=i,group_size=len(b['mapping']),
                tasks=len(group),return_choices=sum(pops),local_optima=sum(counts),
                mean_task_local_fraction=mean(c/n for c,n in zip(counts,pops)),
                min_task_optima=min(counts),median_task_optima=median(counts),max_task_optima=max(counts),
                critical=int(226 in b['mapping'])))
    save('chain_summary.csv',chain_summary)
    describe_positions(detail,margin)
    freq=Counter((r['stage'],r['locally_optimal_chains']) for r in energy)
    save('chain_count_distribution.csv',[dict(stage=st,locally_optimal_chains=k,returned_count=n) for (st,k),n in sorted(freq.items())])
    grouped={}
    for r in detail:
        key=(r['stage'],r['chain'],r['position'],r['candidate']); counts=grouped.setdefault(key,[0,0])
        counts[0]+=1;counts[1]+=r['q_excess']
    save('chain_position_identity.csv',[dict(stage=st,chain=b,position=p,candidate=c,A=dictionary[c]['A'],B=dictionary[c]['B'],returned_count=n,suboptimal_count=n*int(q[c]>minimum[b-1]),q_excess_sum=x) for (st,b,p,c),(n,x) in sorted(grouped.items())])
    for st in ('pilot','formal'):
        rr=[r for r in margin if r['stage']==st]
        print(st,'selected margin min/median/max',min(r['selected_margin'] for r in rr),median(r['selected_margin'] for r in rr),max(r['selected_margin'] for r in rr),'set margin min/median/max',min(r['set_min_margin'] for r in rr),median(r['set_min_margin'] for r in rr),max(r['set_min_margin'] for r in rr))
if __name__=='__main__':main()
