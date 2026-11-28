"""Fixed exploratory eight-cell grid; one primary SA schedule, no repair."""
import argparse, concurrent.futures, time
from common import *
from representation import quantize,legal_energies
import pandas as pd

def construct_fill(W,mask,encoding,lam,fill):
    m=float(W[mask].min());R=float(np.ptp(W[mask]));C=np.where(mask,W-m,fill*R)
    u=np.zeros(52);v=np.zeros(52)
    if encoding=='rc':u=C.min(1);v=(C-u[:,None]).min(0)
    D=C-u[:,None]-v[None,:];assert D.min()>=-1e-12
    Q=np.zeros((104,104));Q[:52,52:]=D
    for start,potential in [(0,u),(52,v)]:
        for i in range(52):
            Q[start+i,start+i]=potential[i]-lam
            for j in range(i+1,52):Q[start+i,start+j]=2*lam
    off=Q.copy();np.fill_diagonal(off,0);J=np.zeros((105,105))
    J[:104,:104]=-(off+off.T)/8
    J[:104,104]=J[104,:104]=-(np.diag(Q)/4+(off+off.T).sum(1)/8)
    offset=np.trace(Q)/2+off.sum()/4+2*lam
    err=float(np.max(np.abs(legal_energies(J,52,52)+offset-C)))
    assert err<1e-8
    from kaiwu.core import qubo_matrix_to_ising_matrix
    sdk,bias=qubo_matrix_to_ising_matrix(Q)
    np.testing.assert_allclose(J,sdk,rtol=1e-14,atol=1e-12)
    return J,dict(m=m,R=R,lam=lam,fill_multiplier=fill,forbidden_fill=fill*R,
                  offset=float(offset),float_equivalence_max_abs=err)

def prepare(args):
    reg=verify_registration(args.registration_anchor);ar=read(REG/'A_receipt.json')
    assert ar['selected'] is None and not ar['B_cancelled']
    write_new(OUT/'B_prepare_started.json',dict(time=now(),A_receipt_sha256=sha(REG/'A_receipt.json')))
    W,mask,keys=pool();rows=[]
    for cell in reg['B_grid']:
        ident=cell['id'];enc=cell['encoding'];fill=cell['fill_multiplier']
        J,meta=construct_fill(W,mask,enc,cell['lambda_value'],fill)
        K,factor=quantize(J);meta.update(max_abs_J=float(np.abs(J).max()),quant_scale=factor,
            quantization_step=float(np.abs(J).max()/127),max_abs_reference=float(np.abs(J[:104,104]).max()),
            unique_integer_coefficients=int(len(np.unique(K))))
        save_array(OUT/'inputs'/f'{ident}_real_J.npy',J)
        if fill==1:
            stage='p2_rescue1' if '-theta-' in ident else 'p2_v2'
            oldid=f'11-{enc}-N8'+('-rescue1' if stage=='p2_rescue1' else '')
            old=ROOT/f'artifacts/{stage}/representations/{oldid}.npz'
            oldrow=read(old.with_suffix('.json'));np.testing.assert_array_equal(K,np.load(old)['J'])
            cert=read(old.with_suffix('.certificate.json'))
            row=dict(oldrow,id=ident,G1=cert['status'],G2='PASS' if oldrow['worst_ground_regret']<=.1 else 'FAIL',
                     status=cert['status'],meta=meta,matrix_file=str(old.relative_to(ROOT)),matrix_sha256=sha(old),
                     reused_from=oldid,source='fixed_grid')
        else:
            row=matrix_audit(ident,K,meta);row.update(source='fixed_grid',reused_from=None)
        rows.append(row)
        print(json.dumps(dict(id=ident,G1=row['G1'],G2=row['G2'],max_abs_J=meta['max_abs_J'],quantization_step=meta['quantization_step'],reused=row['reused_from'])),flush=True)
    for ident in ar['B_extra_candidates']:
        rows.append(dict(next(r for r in ar['candidates'] if r['id']==ident),source='A_G1_pass_G2_fail',reused_from=ident))
    write_new(REG/'B_manifest.json',dict(time=now(),registration_anchor=args.registration_anchor,
        A_receipt_sha256=sha(REG/'A_receipt.json'),candidates=rows,code_file=str(Path(__file__).relative_to(ROOT)),code_sha256=sha(Path(__file__)),
        protocol_sha256=sha(PROTOCOL),restarts_per_candidate=1000,blocks=10,samples_per_block=100))

def verify_B(commit):
    assert len(commit)==40
    for name in ['codex/p2_dual_rescue/B_manifest.json','codex/p2_dual_rescue/A_receipt.json']:
        assert subprocess.check_output(['git','show',f'{commit}:{name}'],cwd=ROOT)==(ROOT/name).read_bytes()
    manifest=read(REG/'B_manifest.json');verify_registration(manifest['registration_anchor'])
    assert sha(ROOT/manifest['code_file'])==manifest['code_sha256']
    for row in manifest['candidates']:assert sha(ROOT/row['matrix_file'])==row['matrix_sha256']
    return manifest

def job_run(job):
    import kaiwu as kw
    row,b=job;dest=OUT/'SA_B'/row['id'];dest.mkdir(parents=True,exist_ok=True)
    path=dest/f'block_{b:02}.json';assert not path.exists()
    z=np.load(ROOT/row['matrix_file']);K=z['J'];mask=z['allowed'];W=z['W'];keys=z['keys'];best=float(W[mask].min())
    scale=float(4*np.abs(K).sum(1).max());assert scale>0
    start=time.monotonic();records=[]
    for r in range(100):
        seed=230026+100*b+r;began=time.monotonic();item=dict(restart=r,seed=seed)
        try:
            solver=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=scale,cutoff_temperature=1e-4*scale,alpha=.99,iterations_per_t=10,size_limit=1,rand_seed=seed,process_num=1)
            raw=np.asarray(solver.solve(K));assert raw.shape==(1,105) and np.isin(raw,[-1,1]).all()
            spin=raw[0].astype(np.int64);x=(spin[:-1]*spin[-1]+1)//2
            ac=int(x[:52].sum());bc=int(x[52:].sum());i=int(x[:52].argmax());j=int(x[52:].argmax())
            feasible=ac==1 and bc==1 and bool(mask[i,j])
            item.update(status='VALID_COMPLETED',spins=spin.tolist(),A_count=ac,B_count=bc,feasible=feasible,
                energy=int(-spin@K@spin),key=str(keys[i,j]) if ac==bc==1 else None,
                regret=float(W[i,j]-best) if feasible else None)
        except Exception as e:item.update(status='COMPUTATION_FAILED',error_type=type(e).__name__)
        item['seconds']=time.monotonic()-began;records.append(item)
    feasible=[x for x in records if x.get('feasible') and x['status']=='VALID_COMPLETED']
    chosen=min(feasible,key=lambda x:(x['energy'],tie(x['key']),x['restart'])) if feasible else None
    block=dict(id=row['id'],block=b,initial_temperature=scale,cutoff_temperature=scale*1e-4,
        elapsed_seconds=time.monotonic()-start,restarts=records,selected_restart=chosen['restart'] if chosen else None,
        selected_regret=chosen['regret'] if chosen else None,selected_key=chosen['key'] if chosen else None,
        oracle_any_regret_le2=any(x['regret']<=2 for x in feasible))
    write_new(path,block)
    return dict(id=row['id'],block=b,valid=sum(x['status']=='VALID_COMPLETED' for x in records),feasible=len(feasible),selected_regret=block['selected_regret'])

def summarize(manifest):
    summaries=[];sample_rows=[];block_rows=[]
    for row in manifest['candidates']:
        blocks=[read(OUT/'SA_B'/row['id']/f'block_{b:02}.json') for b in range(10)]
        records=[x for block in blocks for x in block['restarts']]
        assert len(records)==1000
        f=[x for x in records if x.get('feasible') and x['status']=='VALID_COMPLETED']
        valids=sum(x['status']=='VALID_COMPLETED' for x in records);nr=len(f)
        vals=sorted(float(b['selected_regret']) if b['selected_regret'] is not None else float('inf') for b in blocks)
        median=(vals[4]+vals[5])/2
        regrets=[x['regret'] for x in f]
        s=dict(id=row['id'],source=row['source'],G1=row['G1'],G2=row['G2'],max_abs_J=row['meta']['max_abs_J'],
            quantization_step=row['meta'].get('quantization_step',row['meta']['max_abs_J']/127),
            valid_returns=valids,feasible_raw=nr,feasible_rate=nr/1000,conditional_feasible_rate=nr/valids if valids else None,
            blocks_with_feasible=sum(b['selected_regret'] is not None for b in blocks),
            selected_block_successes=sum(b['selected_regret'] is not None and b['selected_regret']<=2 for b in blocks),
            selected_block_success_rate=sum(b['selected_regret'] is not None and b['selected_regret']<=2 for b in blocks)/10,
            oracle_block_success_rate=sum(b['oracle_any_regret_le2'] for b in blocks)/10,
            block_regret_median=median,block_regret_median_is_infinite=bool(np.isinf(median)),
            feasible_regret_q05=float(np.quantile(regrets,.05)) if regrets else None,
            feasible_regret_median=float(np.median(regrets)) if regrets else None,
            feasible_regret_q95=float(np.quantile(regrets,.95)) if regrets else None,
            eligible=bool(nr>100 and median<=2),matrix_file=row['matrix_file'],matrix_sha256=row['matrix_sha256'])
        summaries.append(s)
        for b in blocks:
            block_rows.append({k:v for k,v in b.items() if k!='restarts'})
            for x in b['restarts']:sample_rows.append(dict(id=row['id'],block=b['block'],**{k:v for k,v in x.items() if k!='spins'}))
    dest=OUT/'results';dest.mkdir()
    pd.DataFrame(summaries).to_csv(dest/'B_full_grid.csv',index=False,float_format='%.17g')
    pd.DataFrame(block_rows).to_csv(dest/'B_block_metrics.csv',index=False,float_format='%.17g')
    pd.DataFrame(sample_rows).to_csv(dest/'B_all_samples.csv',index=False,float_format='%.17g')
    eligible=sorted([s for s in summaries if s['eligible']],key=lambda s:(-s['feasible_raw'],s['id']))
    chosen=eligible[0] if eligible else None
    receipt=dict(time=now(),stage='B',framework='EXPLORATORY_POST_HOC_FILTERED_HARDWARE',
        status='SELECTED_EXPLORATORY' if chosen else 'NO_ELIGIBLE_CONFIGURATION',selected=chosen['id'] if chosen else None,
        selected_matrix_sha256=chosen['matrix_sha256'] if chosen else None,candidates=summaries,
        B_manifest_sha256=sha(REG/'B_manifest.json'),results_sha256=sha(dest/'B_full_grid.csv'),
        selection_rule=read(REG/'registration.json')['selection_B'],cim_submissions=0)
    write_new(REG/'B_receipt.json',receipt)
    print('SELECTION',receipt['selected'],sha(REG/'B_receipt.json'),flush=True)

def run(args):
    manifest=verify_B(args.anchor);write_new(OUT/'B_SA_started.json',dict(time=now(),anchor=args.anchor,candidates=len(manifest['candidates']),restarts=len(manifest['candidates'])*1000))
    jobs=[(r,b) for r in manifest['candidates'] for b in range(10)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,initializer=initialize_license) as executor:
        for result in executor.map(job_run,jobs):print(json.dumps(result),flush=True)
    summarize(manifest)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run']);p.add_argument('--registration-anchor');p.add_argument('--anchor');args=p.parse_args()
    prepare(args) if args.mode=='prepare' else run(args)
