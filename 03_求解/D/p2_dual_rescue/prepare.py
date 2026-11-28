"""Freeze QUBO and Ising inputs; does not invoke mutate, SA or hardware."""
import importlib.util, importlib.metadata, platform
from common import *
from representation import construct,quantize,legal_energies

def main():
    assert not (REG/'registration.json').exists()
    OUT.mkdir();(OUT/'inputs').mkdir();REG.mkdir()
    W,mask,keys=pool();R=float(np.ptp(W[mask]));lam=31.012015773309233
    inputs={};candidates=[]
    for encoding,seed in [('raw',240028),('rc',240029)]:
        J,meta,Q=construct(W,mask,encoding,lam/R)
        old=ROOT/f'artifacts/p2_rescue1/representations/11-{encoding}-N8-rescue1.npz'
        K,_=quantize(J);np.testing.assert_array_equal(K,np.load(old)['J'])
        np.testing.assert_allclose(legal_energies(J,52,52)+meta['offset'],np.where(mask,W-W[mask].min(),R),rtol=0,atol=1e-8)
        qpath=OUT/'inputs'/f'{encoding}_Q.npy';jpath=OUT/'inputs'/f'{encoding}_J.npy'
        save_array(qpath,Q);save_array(jpath,J)
        for p in [qpath,jpath]:inputs[str(p.relative_to(ROOT))]=sha(p)
        candidates.append(dict(id=f'A-{encoding}-M8',encoding=encoding,external_seed=seed,
                               Q=str(qpath.relative_to(ROOT)),J=str(jpath.relative_to(ROOT)),meta=meta))
    frozen=read(ROOT/'codex/p2_rescue1/freeze.json');protected=dict(frozen['protected'])
    for base in [ROOT/'artifacts/p2_rescue1',ROOT/'codex/p2_rescue1']:
        for p in base.rglob('*'):
            if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
    paper=ROOT/'00_赛题与规则/官方发布/2026论文规范与模板/APMCM LaTeX 模板'
    for p in (ROOT/'artifacts/p2_rescue1/paper_before').rglob('*'):
        if p.is_file():
            live=paper/p.relative_to(ROOT/'artifacts/p2_rescue1/paper_before')
            assert sha(live)==sha(p);protected[str(live.relative_to(ROOT))]=sha(live)
    for n,h in protected.items():assert sha(ROOT/n)==h,n
    inputs[str(PROTOCOL.relative_to(ROOT))]=sha(PROTOCOL)
    inputs['artifacts/p23_v2/pool_11.npz']=sha(ROOT/'artifacts/p23_v2/pool_11.npz')
    binary=Path(importlib.util.find_spec('kaiwu.preprocess._precision_adaption_mutate').origin)
    obj=dict(time=now(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
             candidates_A=candidates,protected=protected,input_hashes=inputs,
             code_hashes={str(p.relative_to(ROOT)):sha(p) for p in [*sorted(CODE.glob('*.py')),BASE/'checker.py',BASE/'representation.py',BASE/'p2_common.py']},
             environment=dict(python=platform.python_version(),numpy=np.__version__,kaiwu=importlib.metadata.version('kaiwu'),
                              mutate_binary_path=str(binary),mutate_binary_sha256=sha(binary)),
             mutate=dict(iterations=100,heuristic='greedy',decision='heuristic',timeout_seconds=600,calls_per_candidate=1),
             B_grid=[dict(id=f'B-{label}-{enc}-fill{fill}',lambda_value=l,encoding=enc,fill_multiplier=fill)
                     for label,l in [('theta',lam),('R',1.1*R)] for enc in ['raw','rc'] for fill in [1,2]],
             B_schedules=1,B_restarts_per_candidate=1000,B_blocks=10,B_samples_per_block=100,
             selection_B=['feasible_raw_count>100','median_energy_selected_block_regret_with_inf<=2','max_feasible_raw_count','lexical_id'],
             new_fits_authorized=0,paper_writes_authorized=False,SPQC1000_authorized=False)
    write_new(REG/'registration.json',obj)
    print('registration',sha(REG/'registration.json'),'inputs',inputs,'protected',len(protected))

if __name__=='__main__':main()
