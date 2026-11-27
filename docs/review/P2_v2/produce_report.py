"""Read-only independent audit of frozen P2 outputs; writes derived reports only."""
from pathlib import Path
import sys,json,hashlib,itertools,subprocess
from datetime import datetime
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'03_求解/D/p2_v2'))
from p2_common import OUT,P23,REG,read,write_new,sha,now,anchor,verify_inputs,tie
from task_stats import summarize

COMMIT='5528cae132206a30b6f921905da6f30704ad15c5'

def main():
    receipt=anchor(COMMIT);verify_inputs()
    results=OUT/'results';results.mkdir(exist_ok=True)
    audit=read(OUT/'representation_audits.json');meta={r['id']:r for r in audit}
    rows=[];summary=[];nchecked=0
    start=read(OUT/'sa_started.json')
    commit_time=subprocess.check_output(['git','show','-s','--format=%cI',COMMIT],cwd=ROOT,text=True).strip()
    assert datetime.fromisoformat(start['time'])>=datetime.fromisoformat(commit_time)
    expected={(r['id'],t,b) for r in receipt['sa_matrices'] for t in ('scaled','fixed') for b in range(20)}
    got=set()
    for path in sorted((OUT/'sa').glob('*.json')):
        block=read(path);key=(block['id'],block['temperature'],block['block']);assert key in expected and key not in got;got.add(key)
        record=meta[block['id']];z=np.load(ROOT/record['matrix_file']);J=z['J'];mask=z['allowed'];W=z['W'];keys=z['keys'];n=mask.shape[0]
        attempt=block['restarts'];assert len(attempt)==100
        valid=[r for r in attempt if r['status']=='VALID_COMPLETED'];assert len(valid)==100
        S=np.asarray([r['spins'] for r in valid],dtype=np.int64);assert S.shape==(100,len(J)) and np.isin(S,[-1,1]).all()
        # Independently decode every returned spin and recalculate energies in a batch.
        energies=-np.sum((S@J)*S,axis=1)
        binary=(S[:,:-1]*S[:,-1,None]+1)//2
        af=binary[:,:n].sum(axis=1)==1;bf=binary[:,n:].sum(axis=1)==1
        pairs=np.argwhere(mask);lowest=float(W[mask].min());ereg=[];rreg=[];nfeas=0;rep_keys=[]
        original=[];integer_hits=0;onehot_count=0
        emin=float(record.get('best_integer_energy',np.nan))
        if not np.isfinite(emin):
            ens=pd.read_csv(OUT/'representations'/f"{block['id']}.energies.csv",float_precision='round_trip');emin=ens.loc[ens.allowed,'energy'].min()
        for i,r in enumerate(valid):
            assert r['restart']==i and r['seed']==230026+100*block['block']+i
            assert abs(float(energies[i])-r['energy'])<=1e-9*max(1.,abs(r['energy']))
            a=binary[i,:n];b=binary[i,n:];one=bool(af[i] and bf[i]);onehot_count+=one
            feasible=one and bool(mask[a.argmax(),b.argmax()]);assert feasible==r['feasible']
            if feasible:
                v=float(W[a.argmax(),b.argmax()]-lowest);assert abs(v-r['regret'])<1e-12
                ereg.append(v);nfeas+=1;original.append(str(keys[a.argmax(),b.argmax()]))
                integer_hits+=bool(abs(float(energies[i])-emin)<1e-8)
            else:assert r['regret'] is None
            # Independent repair selection with explicit Hamming distance on legal states.
            dist=a.sum()+b.sum()+2-2*(a[pairs[:,0]]+b[pairs[:,1]])
            chosen=pairs[dist==dist.min()]
            aidx,bidx=min(chosen.tolist(),key=lambda ij:tie(keys[tuple(ij)]))
            assert r['repaired_key']==keys[aidx,bidx] and r['repair_distance']==int(dist.min())
            rv=float(W[aidx,bidx]-lowest);assert abs(rv-r['repaired_regret'])<1e-12;rreg.append(rv);rep_keys.append(r['repaired_key'])
        nchecked+=len(valid)
        row=dict(id=block['id'],pool=record['pool'],encoding=record['encoding'],precision=record['kind'],temperature=block['temperature'],
            block=block['block'],slot=f"F{block['block']+1:02d}",status='VALID_COMPLETED',n_returned=len(valid),n_onehot=onehot_count,n_feasible=nfeas,
            best_regret=min(ereg) if ereg else None,n_near=sum(v<=.1 for v in ereg),n_exact=sum(v==0 for v in ereg),
            feasible_integer_opt_hits=integer_hits,unique_feasible=len(set(original)),
            n_feasible_repaired=len(rreg),best_regret_repaired=min(rreg),n_near_repaired=sum(v<=.1 for v in rreg),
            n_exact_repaired=sum(v==0 for v in rreg),unique_repaired=len(set(rep_keys)),
            seconds=block['elapsed_seconds'],solve_seconds=sum(r['solve_seconds'] for r in valid),
            decode_repair_seconds=sum(r['decode_repair_seconds'] for r in valid),certificate=record['certificate'])
        rows.append(row)
    assert got==expected and nchecked==32000
    frame=pd.DataFrame(rows);frame.to_csv(results/'sa_task_results.csv',index=False,float_format='%.17g')
    for (ident,temp),part in frame.groupby(['id','temperature'],sort=True):
        rr=part.to_dict('records');raw=summarize(rr);repaired=summarize(rr,True)
        write_new(results/f'{ident}_{temp}_task_statistics.json',dict(raw=raw,repaired=repaired))
        row=dict(method='SA',id=ident,temperature=temp,planned_tasks=20,attempted_tasks=20,valid_tasks=20,
            restarts=int(part.n_returned.sum()),raw_feasible=int(part.n_feasible.sum()),raw_near=int(part.n_near.sum()),raw_exact=int(part.n_exact.sum()),
            task_feasible=raw['N_F'],task_near=raw['N_epsilon'],end_to_end_near=raw['end_to_end_success'],conditional_near=raw['conditional_hardware_success'],
            slot_near=raw['slot_success'],best_regret=min(raw['conditional_regret']) if raw['conditional_regret'] else None,
            raw_conditional_task_regret_median=float(np.median(raw['conditional_regret'])) if raw['conditional_regret'] else None,
            task_near_repaired=repaired['N_epsilon'],best_regret_repaired=min(repaired['conditional_regret']),
            certificate=part.certificate.iloc[0],summed_block_seconds=float(part.seconds.sum()))
        summary.append(row)
    missing=[r for r in audit if r['kind']=='M8']
    for r in missing:
        for temp in ('scaled','fixed'):summary.append(dict(method='SA',id=r['id'],temperature=temp,planned_tasks=20,attempted_tasks=0,valid_tasks=0,restarts=0,certificate='UNKNOWN',status='MATRIX_NOT_GENERATED'))
    formal=read(OUT/'formal_slots_initial.json');cim=summarize(formal);assert cim['N_A']==0
    write_new(results/'cim_current_status.json',dict(time=now(),not_T_snap=True,stage='NOT_READY',selection_status=receipt['status'],raw=cim,
        submitted=0,charged_calls_this_run=0,actual_account_balance=None,quota_channel_contract='NOT_CHECKED: no certified submission candidate',slots=formal))
    summary.append(dict(method='CIM',id='NO_ELIGIBLE_CONFIGURATION',temperature='NA',planned_tasks=20,attempted_tasks=0,valid_tasks=0,restarts=0,slot_near=0,status='NOT_READY'))
    pd.DataFrame(summary).to_csv(results/'P2_final_experiment_table.csv',index=False,float_format='%.17g')
    rep=[]
    for r in audit:
        rep.append({k:r.get(k) for k in ['id','pool','encoding','kind','certificate','certificate_reason','float_equivalence_max_abs','best_integer_energy','ground_count','worst_ground_regret','best_ground_regret','top20_retention','top20_min','top20_max','R','epsilon_over_R']})
    pd.DataFrame(rep).to_csv(results/'representation_summary.csv',index=False,float_format='%.17g')
    # Conditional model dispersion and candidate ranks, never new target selection.
    stability=[]
    for pool in ('07','11'):
        z=np.load(P23/f'pool_{pool}.npz');mask=z['allowed'][:,:,0];W=z['vhat'][:,:,0][mask];members=z['members'][:,:,0,:][mask]
        allkeys=np.array([[f'{a}|{b}|NO2' for b in z['B']] for a in z['A']]);keys=allkeys[mask];h=np.array([tie(k) for k in keys])
        ranks=np.empty(members.shape,int)
        for b in range(20):
            order=np.lexsort((h,members[:,b]));ranks[order,b]=np.arange(1,len(keys)+1)
        regs=members-members.min(axis=0);worst=regs.max(axis=1);cvar=np.sort(regs,axis=1)[:,-2:].mean(axis=1)
        choices=dict(mean=np.lexsort((h,W))[0],minimax=np.lexsort((h,worst))[0],cvar90=np.lexsort((h,cvar))[0])
        for name,i in choices.items():
            stability.append(dict(pool=pool,scenario=name,key=keys[i],vhat=W[i],mean_table_regret=W[i]-W.min(),
                rank_min=int(ranks[i].min()),rank_median=float(np.median(ranks[i])),rank_max=int(ranks[i].max()),top5_frequency=float(np.mean(ranks[i]<=5)),top20_frequency=float(np.mean(ranks[i]<=20)),
                regret_p50=float(np.quantile(regs[i],.5)),regret_p90=float(np.quantile(regs[i],.9)),regret_p95=float(np.quantile(regs[i],.95)),worst_regret=worst[i],cvar90=cvar[i]))
        pd.DataFrame(ranks,index=keys,columns=[f'member_{b:02d}' for b in range(20)]).to_csv(results/f'member_ranks_{pool}.csv')
    pd.DataFrame(stability).to_csv(results/'scenario_decisions.csv',index=False,float_format='%.17g')
    costs=[]
    for stage,path in [('training',P23/'training.log'),('representation_audit',OUT/'audit.log'),('SA',OUT/'sa.log')]:
        times=subprocess.check_output(['stat','-c','%w|%y',str(path)],text=True).strip().split('|')
        starttime,endtime=[pd.Timestamp(t) for t in times]
        costs.append(dict(stage=stage,seconds=(endtime-starttime).total_seconds(),basis='filesystem log creation to final write; process interval, includes startup',start=times[0],end=times[1]))
    fit=read(P23/'manifest.json');events=[json.loads(x) for x in (P23/'fit_attempts.jsonl').read_text().splitlines()]
    costs.append(dict(stage='tree_fit_subset',seconds=sum(x.get('seconds',0) for x in events if x['event']=='finish'),basis='measured fit timers; subset of training, do not add again'))
    for stage in ['CIM_upload','CIM_queue','CIM_device','CIM_decode']:
        costs.append(dict(stage=stage,seconds=None,basis='NOT_RUN'))
    pd.DataFrame(costs).to_csv(results/'cost_ledger.csv',index=False)
    write_new(results/'verification.json',dict(time=now(),status='PASS_LOCAL_ONLY',anchor_commit=COMMIT,selection_receipt_sha256=sha(REG/'selection_receipt.json'),
        sa_after_anchor=True,sa_checked_spins=nchecked,sa_blocks=len(got),fit_attempts=fit['actual_fit_attempts'],global_fit_count=fit['global_fit_count'],
        unchanged_protected_files=len(read(REG/'input_freeze.json')['protected']),cim_status='NOT_READY',hardware_calls=0,
        checks=['anchored receipt and all matrix/code hashes','every SA sample energy and independent decoding','every repair without surrogate objective','all restart seeds and block coverage','raw/repaired nested denominators','task failures retained','P1 file protection','CIM zero submissions represented as NOT_STARTED']))
    print(pd.DataFrame(summary).query("temperature == 'scaled' and restarts > 0")[[ 'id','raw_feasible','raw_exact','task_near','best_regret']].to_string(index=False))
    print('PASS: all 32000 SA returns, fixed seeds, repairs, task denominators and protected inputs.')

if __name__=='__main__':main()
