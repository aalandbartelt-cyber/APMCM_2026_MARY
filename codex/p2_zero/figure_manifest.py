"""Index each plot data object, its row count, units, origin and reproduction command."""
import csv
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'figures/P2/data'
REG='codex/p2_zero/'
H='evidence/p2/sha256.json'
META='codex/p2_zero/registration.json'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def index():
    specs={}
    def group(names,fig,source,how,kind,units,denom):
        for name in names.split():specs[name]=(fig,source,how,kind,units,denom)
    h=REG+'hardware_data.py';s=REG+'sa_data.py'
    group('task_margin.csv','F-MARGIN', [H,'evidence/p2/tasks.csv'],h,'deterministic retrospective certificate application','integer energy; original V','25 service tasks; 5 pilot + 20 formal')
    group('return_energy.csv','F-ENERGYHIST;F-MARGIN', [H,'evidence/p2/matrix_certificate.json'],h,'verified historical observations','integer energy; original V; number of chains','250 returned vectors nested in 25 tasks')
    group('chain_detail.csv chain_optimal_250x40.csv chain_task_25x40.csv chain_count_distribution.csv chain_position_identity.csv chain_association.csv chain_summary.csv','F-CHAIN', [H,'evidence/p2/blocks.json','evidence/p2/candidates.csv'],h,'exploratory descriptive, fixed partition','q; rank correlation; counts or task-mean fraction','25 tasks, 250 vectors, 40 distinct groups per vector')
    group('task_timeline.csv','F-TIMELINE',['figures/P2/data/timing_sources.json','evidence/p2/tasks.csv'],h,'client event observations','ISO-8601 UTC+08:00; missing physical times NA','25 service IDs; no optical timing')
    group('timing_sources.json','F-TIMELINE',['evidence/p2/tasks.csv'],h,'hash index of local observations','SHA-256; relative source paths','one record per underlying file; events and server ACK/poll records')
    sa=['figures/P2/data/sa_sources.json',META]
    group('sa_attempts.csv sa_budget_blocks.csv sa_budget_curve.csv','F-BUDGET',sa,s,'H07 exploratory; new primary B=5 separately registered; other prefixes descriptive','restarts; count/fraction of planned blocks; original V','cohort and arm kept separate; nested prefixes; long chain n=2 blocks')
    group('sa_paired_test.json','F-BUDGET',sa,s,'registered local paired comparison; selected P2 instance','paired counts; fraction-point difference; two-sided exact p','20 fresh pairs B=5 only; failures are misses')
    group('chain_ablation.csv','P2-A12;F-BUDGET',sa,s,'exploratory matched comparison + historical multiparameter arms','spins; q; integer energy; original V; restart counts','H02/H05 separate; new chain-length comparison 2 paired blocks')
    group('sa_sources.json','F-BUDGET;P2-A12',[META],s,'hash index of raw/configuration inputs','SHA-256; relative source paths','one record per resolved source path')
    ext={p.name for p in D.iterdir() if p.suffix in ('.csv','.json') and p.name!='figure_data_manifest.csv'}
    if ext!=set(specs):raise ValueError('Data objects missing/unindexed: '+str(ext^set(specs)))
    rows=[]
    for name,(fig,sources,script,kind,units,den) in sorted(specs.items()):
        path=D/name
        if path.suffix=='.csv':
            with path.open(newline='') as f:n=sum(1 for _ in csv.DictReader(f))
        else:
            obj=json.loads(path.read_text())
            n=1 if name=='sa_paired_test.json' else len(obj)
        rows.append(dict(file=str(path.relative_to(ROOT)),plot=fig,rows_or_records=n,sha256=digest(path),sources=';'.join(sources),source_sha256=';'.join(digest(ROOT/x) for x in sources),generator=script,generator_sha256=digest(ROOT/script),command='/usr/bin/python3 -B '+script,classification=kind,units=units,denominator_or_key=den,status='VERIFIED'))
    out=D/'figure_data_manifest.csv'
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    print(len(rows),'figure-data files indexed')
if __name__=='__main__':index()
