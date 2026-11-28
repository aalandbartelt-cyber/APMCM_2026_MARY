"""Run the two registered single shots, audit both and seal the decision."""
import argparse,signal,time
from common import *
from representation import quantize

def main():
    p=argparse.ArgumentParser();p.add_argument('--anchor',required=True);args=p.parse_args()
    reg=verify_registration(args.anchor);write_new(OUT/'A_started.json',dict(time=now(),anchor=args.anchor))
    rows=[]
    for row in reg['candidates_A']:
        ident=row['id'];dest=OUT/'mutate'/ident;dest.mkdir(parents=True)
        log=dest/'runtime.log';env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
        with log.open('xb') as stream:
            proc=subprocess.Popen(['/usr/bin/python3',str(CODE/'mutate_once.py'),'--id',ident,'--anchor',args.anchor],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            timed=False
            try:code=proc.wait(timeout=600)
            except subprocess.TimeoutExpired:
                timed=True;os.killpg(proc.pid,signal.SIGTERM)
                try:code=proc.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
        write_new(dest/'process_closeout.json',dict(time=now(),exit_code=code,timeout=timed,log_sha256=sha(log)))
        output=dest/'first_output.npy'
        if not output.exists():
            status='UNKNOWN' if timed else 'IMPLEMENTATION_ERROR'
            audited=dict(id=ident,G1=status,G2='NOT_EVALUATED',status=status,reason='mutate_timeout_no_complete_output' if timed else 'mutate_failed_no_output')
        else:
            try:
                J=np.load(output);assert J.shape==(105,105) and np.isfinite(J).all()
                assert np.array_equal(J,J.T) and np.array_equal(np.diag(J),np.zeros(105))
                K,factor=quantize(J,8)
                audited=matrix_audit(ident,K,dict(row['meta'],max_abs_J=float(np.abs(J).max()),quant_scale=factor,
                                                first_output_file=str(output.relative_to(ROOT)),first_output_sha256=sha(output)))
            except Exception as e:
                audited=dict(id=ident,G1='IMPLEMENTATION_ERROR',G2='NOT_EVALUATED',status='IMPLEMENTATION_ERROR',reason=repr(e))
        rows.append(audited);write_new(OUT/f'{ident}_status.json',audited)
        print(json.dumps({k:audited.get(k) for k in ['id','G1','G2','status','worst_ground_regret','reason']}),flush=True)
    good=sorted([r for r in rows if r['status']=='CERTIFIED'],key=lambda r:(r['worst_ground_regret'],-r['top20_min'],r['id']))
    selected=good[0] if good else None
    receipt=dict(time=now(),stage='A',anchor_registration=args.anchor,status='SELECTED' if selected else 'PROCEED_TO_EXPLORATORY_B',
                 selected=selected['id'] if selected else None,selected_matrix_sha256=selected['matrix_sha256'] if selected else None,
                 candidates=rows,B_cancelled=bool(selected),B_extra_candidates=[r['id'] for r in rows if r['G1']=='CERTIFIED' and r['G2']=='FAIL'],
                 registration_sha256=sha(REG/'registration.json'),code_hashes=reg['code_hashes'],cim_submissions=0)
    write_new(REG/'A_receipt.json',receipt)
    print('A receipt',sha(REG/'A_receipt.json'),'selected',receipt['selected'],flush=True)

if __name__=='__main__':main()
