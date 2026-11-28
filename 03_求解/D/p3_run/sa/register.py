"""Create the prospective formal SA seed ledger without running a solver."""
import csv
import hashlib
import io
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUTPUT = ROOT / 'artifacts/p3_run/B/formal'
ANCHOR = '2e1dab8d3312ad01bac1d71c7edd6ac5fddb7d37'
FAMILIES = ('O3', 'NO2', 'FO2')
BUDGETS = (1, 2, 5, 10, 20, 50, 100)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def create(path, data):
    with path.open('xb') as out:
        out.write(data)


def inspect_history():
    seeds = set()
    files = []
    for dirname in ('p2_zero', 'p2_research_20261128', 'p2_dual_rescue', 'p2_v2'):
        for path in sorted((ROOT / 'artifacts' / dirname).rglob('*')):
            if path.suffix not in {'.json', '.jsonl', '.csv'}:
                continue
            data = path.read_bytes()
            if path.suffix == '.csv':
                table = csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
                names = set(table.fieldnames or ()) & {'seed', 'rand_seed'}
                if not names:
                    continue
                local = {int(row[name]) for row in table for name in names if row[name].isdigit()}
            else:
                local = {int(n) for n in re.findall(rb'"(?:rand_seed|seed)"\s*:\s*(\d+)', data)}
            if local:
                files.append({'source': str(path.relative_to(ROOT)), 'n_distinct': len(local),
                              'sha256': digest(data), 'min': min(local), 'max': max(local)})
                seeds.update(local)
    return seeds, files


def register():
    receipt_bytes = (ROOT / 'evidence/p3/receipt.json').read_bytes()
    committed = subprocess.check_output(['git','-C',str(ROOT),'show',ANCHOR + ':evidence/p3/receipt.json'])
    assert receipt_bytes == committed
    history, sources = inspect_history()
    pilot = {910001 + 1000*j + i for j in range(3) for i in range(48)}
    other_design = {990001 + 1000*j + i for j in range(3) for i in range(8)}
    previous_formula = {300000 + 1000*j + 100*b + i for j in range(3) for b in range(3) for i in range(100)}
    new = 7300000
    rows = [{'family': family, 'block': b+1, 'restart': i+1,
             'seed': new+1000*j+100*b+i} for j,family in enumerate(FAMILIES)
            for b in range(3) for i in range(100)]
    assigned = {row['seed'] for row in rows}
    assert len(assigned) == 900 and not (assigned & (history | pilot | other_design))
    old_overlap = sorted(history & previous_formula)
    assert old_overlap, 'Verify the reason for changing the inherited seed base.'
    stream = io.StringIO(newline='')
    w = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    seed_data = stream.getvalue().encode()
    source_data = json_bytes(sources)
    spec = {'stage':'EXECUTION_PREREGISTRATION_BEFORE_FORMAL_SA','created_utc':datetime.now(timezone.utc).isoformat(),
            'sealed_anchor':ANCHOR,'sealed_receipt_sha256':digest(receipt_bytes),
            'formal_seed_manifest_sha256':digest(seed_data),'seed_history_sources_sha256':digest(source_data),
            'formula':'7300000 + 1000*j + 100*b + i; j=O3,NO2,FO2; b=0..2; i=0..99; display block/restart one-based',
            'seed_family_decision':'Replace the P3-1 seed base only because it overlaps recorded P2 SA restarts, prior to seeing any formal SA outputs.',
            'p2_recorded_distinct_seeds':len(history),'original_formula_p2_overlap':old_overlap,
            'p3_pilot_checked':len(pilot), 'p3_design_reserved':sorted(other_design),
            'intersection_with_observed_history_and_pilot':0, 'gpu_validation_seeds':'separate range, to be checked against actual paired gate seeds before start',
            'conditional_backend':'Validated GPU only after both gates pass; otherwise Kaiwu SDK 1.4.4 CPU, four independent workers.',
            'schedule':{'T0':'4 max_i sum_j abs(J[i,j])','cutoff':'T0*1e-4, as P3-1 and the original Kaiwu CPU trials',
                        'alpha':0.99,'iterations_per_t':490,'size_limit':1,'process_num':1},
            'prefixes':BUDGETS,'primary':'minimum integer energy among strict vectors; tie by restart index; original index within return; NA when no strict vector',
            'strict':'all 40 groups legal in one raw vector; no repair','exact':'primary candidate ID equals the frozen slice winner',
            'denominator':'3 non-overlapping blocks per family; prefixes nested; 100 restarts per block; incomplete prefixes explicitly labeled and not scored',
            'archive':'one untouched, ordered lossless NPY per restart; preserve seed, SHA256, raw dtype, run times, failures; independent energy and decode check',
            'expansion':'not part of formal data; no adaptive stopping or seed replacement'}
    OUTPUT.mkdir(parents=True,exist_ok=True)
    create(OUTPUT/'seed_history_sources.json',source_data)
    create(OUTPUT/'seeds.csv',seed_data)
    create(OUTPUT/'registration.json',json_bytes(spec))
    print('registration',digest((OUTPUT/'registration.json').read_bytes()),'prior-overlap',len(old_overlap))


if __name__ == '__main__':
    register()
