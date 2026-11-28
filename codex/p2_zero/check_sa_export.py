"""Read only the exported project files to re-derive local SA outcomes. No SDK."""
import csv
import hashlib
import json
import sys
import zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'evidence/p2'))
from verify import npy_member, require, validate_mapping

def arm_parameters():
    frozen=json.loads((HERE/'registration.json').read_text())['hashes']
    evidence=ROOT/'evidence/p2'
    extra=HERE/'sa_replay_inputs'
    historical='artifacts/p2_research_20261128/short_H05/'
    paths={'40_real':(evidence/'matrix.npz',evidence/'blocks.json',historical+'40_real/'),
           '40_zero':(extra/'zero_matrix.npz',evidence/'blocks.json',historical+'40_zero/'),
           'single_real':(extra/'single_matrix.npz',extra/'single_blocks.json','artifacts/p2_zero/single_real/')}
    out={}
    for arm,(matrix,mapping,origin) in paths.items():
        for file,name in [(matrix,'matrix.npz'),(mapping,'blocks.json')]:
            require(hashlib.sha256(file.read_bytes()).hexdigest()==frozen[origin+name],'registered matrix contract '+arm)
        n=529 if arm=='single_real' else 490
        with zipfile.ZipFile(matrix) as z:
            J=npy_member(z,'J','<i8',(n,n))
            q=npy_member(z,'q','<i8',(529,))
            v=npy_member(z,'values','<f8',(529,))
        blocks=json.loads(mapping.read_text());validate_mapping(blocks,529,n-1)
        edges=[(i,j,-2*J[i*n+j]) for i in range(n) for j in range(i+1,n) if J[i*n+j]]
        out[arm]=(n,edges,q,v,min(v),blocks)
    return out

def replay():
    params=arm_parameters()
    data=ROOT/'figures/P2/data'
    totals={}
    with (data/'sa_attempts.csv').open(newline='') as f:
        for row in csv.DictReader(f):
            arm=row['arm'];n,edges,q,v,minimum,blocks=params[arm]
            name=(row['source'],arm)
            totals[name]=1+totals.get(name,0)
            if row['status']!='VALID_COMPLETED':
                require(row['hit']=='0' and row['strict']=='0' and not row['bits_hex'],'failed slot')
                continue
            raw=bytes.fromhex(row['bits_hex'])
            require(len(raw)==(n+7)//8 and int(row['spins'])==n,'packed width')
            s=[1 if raw[i//8] & (128>>(i%8)) else -1 for i in range(n)]
            E=sum(k*s[i]*s[j] for i,j,k in edges)
            choices=[]
            for b in blocks:
                flags=[x==s[-1] for x in s[b['start']:b['stop']]]
                t=next((i for i,x in enumerate(flags) if not x),len(flags))
                if not any(flags[t:]):choices.append(b['mapping'][t])
            strict=len(choices)==len(blocks)
            c=min(choices,key=lambda i:(q[i],i)) if choices else None
            regret=v[c]-minimum if c is not None else None
            require((int(row['energy']),int(row['partial']),int(row['strict']),int(row['hit']))==(E,int(bool(choices)),int(strict),int(strict and regret==0)),'outcome: '+str(name))
            require(row['candidate']==('NA' if c is None else str(c)) and (None if row['original_regret']=='NA' else float(row['original_regret']))==regret,'dictionary result')
    expected={('H07','40_real'):500,('H07','40_zero'):500,('fresh','40_real'):2000,('fresh','40_zero'):2000,('fresh','single_real'):200}
    require(totals==expected,'slot denominators')
    print('PASS | 5200 local SA slots (4200 fresh + 1000 historical) | sealed matrices, energies, strict/partial, original regrets and failures')
if __name__=='__main__':replay()
