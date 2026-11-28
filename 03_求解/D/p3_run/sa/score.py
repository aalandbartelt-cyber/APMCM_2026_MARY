"""Replay raw formal SA vectors, compare against the sealed protocol and assemble the seven prefixes."""
import csv
import hashlib
import importlib.util
import io
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np
from register import ROOT, OUTPUT, BUDGETS, FAMILIES, create, digest, json_bytes
from run_formal import load_manifest, tag


def emit(path,data):
    if path.exists():
        if path.read_bytes()!=data:
            raise ValueError('Prior output differs: '+str(path))
    else:
        create(path,data)


def table(name,rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    emit(OUTPUT/name,stream.getvalue().encode())


def sealed_scorer():
    path=ROOT/'evidence/p3/protocol.py'
    spec=importlib.util.spec_from_file_location('anchored_p3_protocol',path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def independent_decode(data,vector):
    """Energy via the upper-triangle edge list; decode one wall in every padded group."""
    m = data['J']
    assert np.array_equal(m,m.T) and not np.any(np.diag(m))
    a,b = np.nonzero(np.triu(m,1))
    s = np.asarray(vector,dtype=np.int64)
    energy=int(-2*np.dot(m[a,b],s[a]*s[b]))
    cand=[]
    dead=[]
    cursor=0
    for g,(lo,hi) in enumerate(zip(data['offsets'][:-1],data['offsets'][1:]),1):
        n=int(hi-lo)-1
        spins=s[cursor:cursor+n]*s[-1]
        walls=np.diff(np.r_[1,spins,-1])
        indices=np.flatnonzero(walls==-2)
        if len(indices)!=1 or np.any(walls>0):
            dead.append(g)
        else:
            cand.append(int(lo)+int(indices[0]))
        cursor+=n
    assert cursor==len(s)-1
    if dead:
        return energy,dead,None
    idx=min(cand,key=lambda i:(int(data['q'][i]),i))
    values=data['values']
    return energy,[],{'candidate_index':idx,'id':int(data['ids'][idx]),
                      'vhat':float(values[idx]),'regret':float(values[idx]-values.min()),
                      'exact':bool(values[idx]==values.min())}


def primary_for(rows):
    valid=[r for r in rows if r['status']=='SCORED' and r['strict']]
    return min(valid,key=lambda r:(r['energy'],r['restart']),default=None)


def score():
    protocol=sealed_scorer()
    launch=json.loads((OUTPUT/'launch.json').read_text())
    assert launch['registration_sha256']==digest((OUTPUT/'registration.json').read_bytes())
    assert launch['registration_addendum_sha256']==digest((OUTPUT/'registration_addendum.json').read_bytes())
    assert launch['gate_sha256']==digest((OUTPUT.parent/'gpu_gate/decision.json').read_bytes())
    runner='run_validated_gpu.py' if launch['backend']=='cuda' else 'run_formal.py'
    assert launch['source_sha256']==digest(Path(__file__).with_name(runner).read_bytes())
    cert=json.loads((ROOT/'evidence/p3/certificates.json').read_text())['batches']
    batches={}
    for f in FAMILIES:
        with np.load(ROOT/'evidence/p3'/(f+'.npz'),allow_pickle=False) as raw:
            batches[f]={k:raw[k] for k in ('J','offsets','q','D','values','ids')}
        assert np.count_nonzero(batches[f]['values']==batches[f]['values'].min())==1
    entries=load_manifest()
    formal_seeds={row['seed'] for row in entries}
    validation_ranges={660001+1000*j+i for j in range(3) for i in range(160)}
    validation_hashes={}
    for kind in ('cpu_vectors.jsonl','gpu_vectors.jsonl'):
        file=OUTPUT.parent/'gpu_gate'/kind
        data=file.read_bytes()
        observed=[json.loads(line)['seed'] for line in data.splitlines()]
        assert len(observed)==480 and set(observed)==validation_ranges
        assert not formal_seeds.intersection(observed)
        validation_hashes[kind]=digest(data)
    assert len(list((OUTPUT/'starts').glob('*.json')))==len(entries)
    assert len(list((OUTPUT/'returns').glob('*.json')))==len(entries)
    all_rows=[]
    index=[]
    hashes=[]
    for item in entries:
        label=tag(item)
        result=json.loads((OUTPUT/'returns'/(label+'.json')).read_text())
        start=json.loads((OUTPUT/'starts'/(label+'.json')).read_text())
        assert all(result[k]==value and start[k]==value for k,value in item.items())
        assert start['started_utc']==result['started_utc']
        f=item['family']
        out={**item,'status':result['status'],'strict':None,'invalid_groups':None,
             'energy':None,'residual':None,'candidate_index':None,'id':None,'vhat':None,'regret':None,'exact':None}
        if 'vector_path' in result:
            path=OUTPUT/result['vector_path']
            sha=digest(path.read_bytes())
            assert sha==result['sha256']
            hashes.append(sha+'  '+result['vector_path']+'\n')
            index.append({**item,'vector_path':result['vector_path'],'sha256':sha,
                          'bytes':path.stat().st_size,'dtype':result['dtype'],'shape':str(result['shape']),
                          'started_utc':result['started_utc'],'finished_utc':result['finished_utc']})
        if result['status']=='RETURNED':
            raw=np.load(path,allow_pickle=False)
            assert raw.shape==(1,490) and str(raw.dtype)==result['dtype']
            judged=protocol.judge_return(f,batches[f],raw)
            if judged['status']!='VALID_COMPLETED':
                raise ValueError((label,judged))
            row=judged['rows'][0]
            energy,dead,decoded=independent_decode(batches[f],raw[0])
            assert row['energy']==energy and row['strict']==(not dead) and row['invalid_groups']==dead,label
            assert row['residual']==energy-cert[f]['ground_energy']
            assert energy>=cert[f]['ground_energy'] and (not dead or row['residual']>=cert[f]['illegal_gap'])
            out.update(status='SCORED',strict=not dead,invalid_groups=','.join(map(str,dead)),
                       energy=energy,residual=row['residual'])
            if decoded:
                assert all(decoded[k]==row[k] for k in decoded),label
                assert row['regret_le_0.1']==decoded['exact']
                out.update(decoded)
        all_rows.append(out)
    assert len({r['vector_path'] for r in index})==len(list((OUTPUT/'vectors').glob('*.npy')))
    table('raw_index.csv',index)
    emit(OUTPUT/'vectors.sha256',''.join(hashes).encode())
    table('formal_results.csv',all_rows)
    subsets={}
    for f in FAMILIES:
        subsets[f]=[[r for r in all_rows if r['family']==f and r['block']==b] for b in (1,2,3)]
    prefixes=[]
    for f,blocks in subsets.items():
        for b,block in enumerate(blocks,1):
            assert [r['restart'] for r in block]==list(range(1,101))
            for budget in BUDGETS:
                rows=block[:budget]
                count=sum(r['status']=='SCORED' for r in rows)
                complete=count==budget
                chosen=primary_for(rows) if complete else None
                base={'family':f,'block':b,'budget':budget,'n_scored':count,'n_strict':sum(r['strict'] is True for r in rows),
                      'prefix_status':('INCOMPLETE' if not complete else 'NO_STRICT' if chosen is None else 'SELECTED')}
                for key in ('restart','seed','energy','residual','candidate_index','id','vhat','regret','exact'):
                    base['selected_'+key]=chosen[key] if chosen else None
                prefixes.append(base)
    table('budget_prefixes.csv',prefixes)
    summary=[]
    for f in FAMILIES:
        for b in BUDGETS:
            s=[r for r in prefixes if r['family']==f and r['budget']==b]
            g=[r for r in s if r['prefix_status']=='SELECTED']
            summary.append({'family':f,'budget':b,'n_blocks_planned':3,'n_blocks_complete':sum(r['prefix_status']!='INCOMPLETE' for r in s),
                            'n_blocks_selected':len(g),'n_exact_planned':sum(r['selected_exact'] is True for r in g),
                            'max_selected_regret_conditional':max((r['selected_regret'] for r in g),default=None)})
    table('budget_summary.csv',summary)
    audit={'planned_restarts':900,'return_status':dict(Counter(r['status'] for r in all_rows)),
           'verified_raw_files':len(index),'individual_sha256_verified':True,'separate_upper_triangle_energy_and_wall_decode_verified':True,
           'protocol_sha256':digest((ROOT/'evidence/p3/protocol.py').read_bytes()),
           'scoring_script_sha256':digest(Path(__file__).read_bytes()),
           'formal_intersection_with_observed_gate_seeds':0,'validation_vectors_sha256':validation_hashes,
           'outputs':{n:digest((OUTPUT/n).read_bytes()) for n in ('raw_index.csv','vectors.sha256','formal_results.csv','budget_prefixes.csv','budget_summary.csv')}}
    emit(OUTPUT/'verification.json',json_bytes(audit))
    print(json.dumps(audit,indent=2))


if __name__=='__main__':
    score()
