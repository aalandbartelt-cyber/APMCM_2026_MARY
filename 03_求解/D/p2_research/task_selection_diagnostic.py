"""Post-hoc task selection diagnostic; preserves all states and uses no solver."""
from pathlib import Path
import csv,json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'artifacts/p2_research_20261128';V=BASE/'validation_H07_H08'

def rows(p):return [json.loads(s) for s in p.read_text().splitlines()]

def analyze(name,rs,q,calls):
    ok=[r for r in rs if r['status']=='VALID_COMPLETED' and r.get('all_chains_feasible',False) and r.get('candidate') is not None]
    a=min(ok,key=lambda r:(r['energy'],r['index'])) if ok else None
    b=min(ok,key=lambda r:(q[r['candidate']],r['candidate'],r['index'])) if ok else None
    return dict(name=name,composite_units=len(rs),SA_call_slots=calls,strict_units=len(ok),
        energy_selected_index=a['index'] if a else None,energy_selected_regret=a['regret'] if a else None,
        business_selected_index=b['index'] if b else None,business_selected_regret=b['regret'] if b else None,
        note='Post-hoc diagnostic: minimum physical energy then earliest index versus minimum(q,candidate,index); strict states only; no new selection or sampling')

def main():
    result=[]
    for kind in ['real','zero']:
        for i in range(5):
            p=V/f'blind_{kind}_{i:02d}';z=np.load(p/'matrix.npz');result.append(analyze(p.name,rows(p/'raw.jsonl'),z['q'],100))
        rs=json.loads((BASE/'final_summary'/f'full_merged_{kind}.json').read_text())
        batches=[rows(V/f'full_batch{i}_{kind}'/'raw.jsonl') for i in range(5)]
        for r in rs:
            if r['status']=='VALID_COMPLETED':r['energy']=sum(b[r['index']]['energy'] for b in batches)
        q=np.load(V/f'full_batch0_{kind}/matrix.npz')['q'];result.append(analyze(f'full_merged_{kind}',rs,q,500))
    with (BASE/'final_summary/task_selection_diagnostic.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
