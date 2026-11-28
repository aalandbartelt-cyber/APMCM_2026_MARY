"""Apply all nine preregistered equivalence checks without using formal baseline data."""
import csv
import hashlib
import json
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
from pathlib import Path
import sys
import numpy as np
from scipy.stats import binomtest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=ROOT/'artifacts/p3_run/B/gpu_gate'
REG=json.loads((OUT/'preregistration.json').read_text())
sys.path.insert(0,str(ROOT/'evidence/p3'))
from protocol import judge_return

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def archive_results():
    paired={}
    for device in ('cpu','gpu'):
        rows=[json.loads(s) for s in (OUT/f'{device}_vectors.jsonl').read_text().splitlines()]
        assert len(rows)==len(REG['families'])*REG['n_per_family']
        for j,family in enumerate(REG['families']):
            part=[r for r in rows if r['family']==family]
            seeds=[r['seed'] for r in part]
            assert seeds==[660001+j*1000+i for i in range(REG['n_per_family'])]
            mat=np.load(ROOT/'evidence/p3'/f'{family}.npz')
            assert sha(ROOT/'evidence/p3'/f'{family}.npz')==REG['bundle_sha'][family]
            result=judge_return(family,mat,[r['vector'] for r in part])
            if result['status']!='VALID_COMPLETED': raise ValueError(result)
            for seed,r in zip(seeds,result['rows']):
                pair=paired.setdefault((family,seed),{'family':family,'seed':seed})
                pair.update({f'{device}_'+k:v for k,v in dict(strict=int(r['strict']),
                            hit=int(r['strict'] and r['exact']),energy=r['energy'],residual=r['residual']).items()})
    records=list(paired.values())
    with (OUT/'paired_outcomes.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return records

ALPHA=.05/9

def binary_gate(cpu,gpu):
    diff=gpu-cpu
    positive=int((diff==1).sum())
    negative=int((diff==-1).sum())
    n=len(diff)
    k=positive+negative
    mass=binomtest(k,n).proportion_ci(confidence_level=1-ALPHA/2)
    if k:
        conditional=binomtest(positive,k).proportion_ci(confidence_level=1-ALPHA/2)
        interval=(conditional.low,conditional.high)
    else:
        interval=(0,1)
    extrema=[q*(2*p-1) for q in [mass.low,mass.high] for p in interval]
    lo,hi=min(extrema),max(extrema)
    return dict(cpu=int(cpu.sum()),gpu=int(gpu.sum()),n=n,estimate=float(diff.mean()),ci=[lo,hi],
                discordant_up=positive,discordant_down=negative,
                equivalence_margin=.12,passed=bool(-.12<=lo and hi<=.12))

def cdf_gate(cpu,gpu,rng):
    grid=np.unique(np.r_[cpu,gpu])
    pair=(gpu[:,None]<=grid).astype(float)-(cpu[:,None]<=grid).astype(float)
    mean=pair.mean(axis=0)
    obs=float(np.max(np.abs(mean)))
    n=len(cpu)
    boots=[]
    for batches in range(0,9999,500):
        size=min(500,9999-batches)
        weights=rng.multinomial(n,np.full(n,1/n),size=size)
        boots.extend(np.max(np.abs(weights@pair/n-mean),axis=1))
    upper=min(1,obs+float(np.quantile(boots,1-ALPHA,method='higher')))
    return dict(estimate=obs,ci_upper=upper,equivalence_margin=.25,passed=bool(upper<=.25),
                cpu_q05_q50_q95=np.quantile(cpu,[.05,.5,.95]).tolist(),
                gpu_q05_q50_q95=np.quantile(gpu,[.05,.5,.95]).tolist())

if __name__=='__main__':
    data=archive_results()
    rng=np.random.default_rng(REG['seed_bootstrap'])
    results={}
    for family in REG['families']:
        by=[r for r in data if r['family']==family]
        measures={}
        for key in ('strict','hit','energy'):
            cpu,gpu=[np.array([r[f'{d}_{key}'] for r in by]) for d in ('cpu','gpu')]
            measures[key]=cdf_gate(cpu,gpu,rng) if key=='energy' else binary_gate(cpu,gpu)
        results[family]=measures
    docs=['preregistration.json','decision.json','exact_steps.json','production_trace_checks.json',
          'cpu_one_proposal.json','size1_probe_followup.json','cpu_vectors.jsonl','gpu_vectors.jsonl',
          'paired_outcomes.csv','schedules.json','supplemental_checks_plan.json','size1_probe_followup_plan.json']
    decision=json.loads((OUT/'decision.json').read_text())
    report=dict(formal_backend=decision['formal_backend'],gpu_gate_passed=decision['gate_passed'],
                retention_counterexample=decision['reason'],exact_enumeration=json.loads((OUT/'exact_steps.json').read_text()),
                production_trace=json.loads((OUT/'production_trace_checks.json').read_text()),
                stats=results,passed_distribution_checks=sum(int(v['passed']) for f in results.values() for v in f.values()),
                total_distribution_checks=9,notes='The interval criteria establish or fail to establish the prespecified practical equivalence bounds at 160 pairs per matrix. A gate failing to establish equivalence alone does not identify a true distribution difference. Energy bounds use a paired empirical bootstrap; binary bounds use two exact binomial intervals; alpha allocation over nine endpoints. The SDK black-box public one-process return differs on a concrete state. Historical P3 quantiles had a relative cutoff; this head-to-head validation and formal B baseline use the current absolute T=0.0001 endpoint.',
                artifact_sha256={d:sha(OUT/d) for d in docs},source_sha256={p.name:sha(p) for p in HERE.glob('*') if p.is_file()})
    with (OUT/'validation_report.json').open('x') as f:
        json.dump(report,f,indent=2,allow_nan=False)
    for f,checks in results.items():
        print(f,[(k,round(v['estimate'],3),v.get('ci',v.get('ci_upper')),v['passed']) for k,v in checks.items()])
