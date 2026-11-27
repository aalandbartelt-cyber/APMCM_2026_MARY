"""One-time preregistration before any P23 fit or P2 solver."""
import csv
import platform
import sys
from pathlib import Path
from p2_common import ROOT,CODE,P1,P23,OUT,REG,DATA,sha,write_new,read,code_hashes,now

def main():
    assert not (REG/'input_freeze.json').exists()
    REG.mkdir(exist_ok=True);P23.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
    public=read(DATA/'sha256_public.json')
    assert all(sha(DATA/name)==value for name,value in public.items())
    amendment=read(P1/'hardening/plan_amendment_freeze.json')
    assert sha(ROOT/'codex/P1_PLANv2.md')==amendment['amended_plan_sha256']
    assert sha(P1/'hardening/protocol.json')==amendment['protocol_sha256']
    assert sha(P1/'hardening/P23_construction_decision.json')==amendment['decision_sha256']
    import json
    ledger=P1/'fit_ledger.jsonl';entries=[json.loads(x) for x in ledger.read_text().splitlines()]
    assert sum(r['event']=='start' for r in entries)==914
    protected={}
    for folder in [P1,ROOT/'03_求解/D/p1_v2',ROOT/'figures',ROOT/'00_赛题与规则/官方发布/2026论文规范与模板/APMCM LaTeX 模板']:
        for p in sorted(folder.rglob('*')):
            if p.is_file() and p!=ledger and '__pycache__' not in p.parts:
                protected[str(p.relative_to(ROOT))]=sha(p)
    training=[CODE/'train.py',CODE/'p2_common.py']
    write_new(REG/'input_freeze.json',dict(time=now(),plan_sha256=sha(ROOT/'codex/P2_PLAN.md'),
        public_hashes=public,protected=protected,training_code={str(p.relative_to(ROOT)):sha(p) for p in training},
        registered_code=code_hashes(),ledger_initial_bytes=ledger.stat().st_size,ledger_initial_sha256=sha(ledger),
        starting_fit_count=914,planned_tree_fits=65,recovery_tree_fits=21,
        tests='tests.py: seven exhaustive/integrity/statistical contracts passed before freeze',
        python=sys.version,platform=platform.platform(),deadlines=dict(T_first_target='2026-11-28T23:59:59+08:00',T_first_latest='2026-11-29T06:00:00+08:00',T_stop='2026-11-29T18:00:00+08:00',T_snap='2026-11-29T21:00:00+08:00'),
        mutate_generation_control='Unavailable compiled internal RNG/tie contract => UNKNOWN, no production invocation; no alternative generator',
        diagnostics_certificate_budget='Coarse cardinality certificate and direct witnesses; B&B only four hardware candidates; UNKNOWN stays public'))
    with (REG/'fit_registration.csv').open('x') as f:
        writer=csv.DictWriter(f,fieldnames=['logical_id','phase','seed','target','usage']);writer.writeheader()
        base=[('full','gate'),('calibration_fold_0','gate'),('calibration_fold_1','gate'),('full','metal'),('full','nonmetal')]
        for n,(phase,target) in enumerate(base,1):writer.writerow(dict(logical_id=f'F{n:03d}',phase=phase,seed=210026,target=target,usage='planned'))
        for b in range(20):
            for j,target in enumerate(['gate','metal','nonmetal']):writer.writerow(dict(logical_id=f'F{6+3*b+j:03d}',phase=f'bootstrap_{b:02d}',seed=211026+b,target=target,usage='data_seed; model_seed=210026'))
        for i in range(1,22):writer.writerow(dict(logical_id=f'R{i:02d}',phase='same_recipe_recovery',usage='failed logical fit only'))
    with (REG/'quota_registration.csv').open('x') as f:
        w=csv.DictWriter(f,fieldnames=['quota_id','phase','formal_slot','machine','mode','sample_number','authorization']);w.writeheader()
        for n in range(1,36):
            phase='pilot' if n<=5 else 'formal' if n<=25 else 'P3_reserve' if n<=30 else 'fault_reserve' if n<=33 else 'cache_reserve'
            w.writerow(dict(quota_id=f'S{n:02d}',phase=phase,formal_slot=f'F{n-5:02d}' if 6<=n<=25 else '',machine='SPQC550',mode='sampling',sample_number=100,authorization='approved_after_gates' if n<=25 else 'separate_approval'))
        for n in (1,2):w.writerow(dict(quota_id=f'L{n:02d}',phase='P2_headline' if n==1 else 'P3_headline',machine='SPQC1000',mode='sampling',sample_number=100,authorization='separate_approval'))
    write_new(OUT/'formal_slots_initial.json',[dict(slot=f'F{i:02d}',quota_id=f'S{i+5:02d}',status='NOT_STARTED') for i in range(1,21)])
    print(dict(protected_files=len(protected),plan_sha256=sha(ROOT/'codex/P2_PLAN.md'),starting_fits=914))

if __name__=='__main__':main()
