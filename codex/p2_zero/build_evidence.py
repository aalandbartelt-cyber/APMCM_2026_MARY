"""Construct a whitelist-only, self-contained package from the local originals."""
from pathlib import Path
import csv,hashlib,json,shutil,subprocess
import numpy as np
R=Path(__file__).resolve().parents[2];O=R/'evidence/p2';C=R/'artifacts/p2_cim_go_20261128'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,rows):
    with (O/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
def main():
    (O/'returns').mkdir(exist_ok=True)
    for n in ['blocks.json','matrix.npz']:shutil.copyfile(C/'input'/n,O/n)
    shutil.copyfile(C/'final_independent_return_audit.json',O/'return_certificate.json')
    seal=json.loads((R/'codex/p2_cim_service/final_seal.json').read_text())
    assert all(sha(R/k)==h for k,h in seal['files'].items())
    z=np.load(C/'input/matrix.npz');s=np.load(R/'artifacts/p23_v2/pool_11.npz')
    orig={(c['A'],c['B'],c['X']):c for c in csv.DictReader((R/'artifacts/p23_v2/pool_11.csv').open())}
    rows=[]
    for k,(i,j) in enumerate(np.argwhere(s['allowed'][:,:,0])):
        a,b=s['A'][i],s['B'][j];c=orig[a,b,'NO2']
        assert float(c['vhat'])==s['vhat'][i,j,0]==z['values'][k]
        rows.append(dict(index=k,id=c['id'],a_axis=i,b_axis=j,A=a,B=b,X='NO2',vhat=float(c['vhat']),q=int(z['q'][k])))
    save('candidates.csv',rows)
    tasks=list(csv.DictReader((R/'codex/P2_CIM_FINAL_EXPERIMENT_TABLE_20261128.csv').open()))
    for t in tasks:
        slot=t['slot'];p=(C/'live/P01/completed_01' if slot=='P01' else C/'service_audit'/slot)/'result.pkl'
        assert sha(p)==t['source_sha256'];shutil.copyfile(p,O/'returns'/f'{slot}.pkl')
    save('tasks.csv',tasks)
    ids=[('research', '5707e3b'),('P01',seal['base_anchor']),('service',seal['service_anchor']),('pre-F01',seal['pilot_gate_and_inference_anchor']),('final','90624a3'),('external review base','41fef1c')]
    save('timeline.csv',[dict(role=k,commit=(v:=subprocess.check_output(['git','rev-parse',i],cwd=R,text=True).strip()),git_time=subprocess.check_output(['git','show','-s','--format=%cI',v],cwd=R,text=True).strip()) for k,i in ids])
    cert=json.loads((R/'artifacts/p2_research_20261128/short_H05/independent_full_audit.json').read_text())['matrices']['40_real']
    (O/'matrix_certificate.json').write_text(json.dumps({k:v for k,v in cert.items() if k!='replay'},indent=2)+'\n')
    files=sorted([*O.glob('*.csv'),*O.glob('*.npz'),*O.glob('*.pkl'),*O.glob('returns/*.pkl'),O/'verify.py',O/'blocks.json',O/'return_certificate.json',O/'matrix_certificate.json'])
    (O/'sha256.json').write_text(json.dumps({str(p.relative_to(O)):sha(p) for p in files},indent=2)+'\n')
if __name__=='__main__':main()
