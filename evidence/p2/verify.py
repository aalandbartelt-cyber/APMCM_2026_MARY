"""Offline verification of the P2 returned solution sets (Python 3.8+, stdlib)."""
import ast
import csv
import hashlib
import io
import json
import math
import pickle
import struct
import zipfile
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def npy_member(archive, key, dtype, shape):
    with archive.open(key + ".npy") as f:
        require(f.read(8) == b"\x93NUMPY\x01\x00", "NPY version")
        n = struct.unpack("<H", f.read(2))[0]
        header = ast.literal_eval(f.read(n).decode("ascii").strip())
        require(header == dict(descr=dtype, fortran_order=False, shape=shape), key + " header")
        count = math.prod(shape)
        return struct.unpack("<" + str(count) + {"<i8":"q", "<f8":"d"}[dtype], f.read())

class Primitives(pickle.Unpickler):
    def find_class(self, module, name):
        raise ValueError("Object globals prohibited")

def spins(path):
    o = Primitives(io.BytesIO(path.read_bytes())).load()
    require(o["format"] == "ndarray-zlib-v1" and tuple(o["shape"]) == (10,490) and o["dtype"]=="<f8", "return format")
    z = zlib.decompressobj()
    raw = z.decompress(o["data"], 39201)
    require(len(raw)==39200 and z.eof and not (z.unconsumed_tail or z.unused_data), "compressed size")
    for s in struct.iter_unpack("<490d", raw):
        require(all(x in (-1,1) for x in s), "invalid spin")
        yield tuple(map(int,s))

def validate_mapping(blocks, total, ref):
    require(all(b["reference"]==ref for b in blocks), "mixed or incorrect reference")
    require(sorted(c for b in blocks for c in b["mapping"])==list(range(total)), "incomplete dictionary")
    require([i for b in blocks for i in range(b["start"],b["stop"])]==list(range(ref)), "spin coverage")
    require(all(len(b["mapping"])==1+b["stop"]-b["start"] for b in blocks), "block dimensions")

def read_model(root):
    blocks=json.loads((root/"blocks.json").read_text())
    validate_mapping(blocks,529,489)
    require(len(blocks)==40,"chain count")
    with zipfile.ZipFile(root/"matrix.npz") as z:
        flat=npy_member(z,"J","<i8",(490,490))
        q=npy_member(z,"q","<i8",(529,))
        v=npy_member(z,"values","<f8",(529,))
    K=[flat[i:i+490] for i in range(0,len(flat),490)]
    candidates=read_csv(root/"candidates.csv")
    require(len(candidates)==529 and len({(c['A'],c['B'],c['X']) for c in candidates})==529,"candidate keys")
    require(sorted(candidates,key=lambda c:(int(c['a_axis']),int(c['b_axis'])))==candidates,"row-major identity")
    R=max(v)-min(v)
    for i,c in enumerate(candidates):
        r=v[i]-min(v)
        u=.375*r if r<=2 else .75+.25*(r-2)/(R-2)
        require((int(c['index']),float(c['vhat']),int(c['q']))==(i,v[i],q[i]) and q[i]==round(63*u),"candidate costs")
    require((candidates[226]['A'],candidates[226]['B'],candidates[226]['X'])==('La','Ti','NO2') and [i for i,x in enumerate(q) if x==0]==[226],"unique optimum")
    allowed=set(); ground=0; illegal=[]; minimum=[]
    for b in blocks:
        ids=range(b["start"],b["stop"]); costs=[q[c] for c in b["mapping"]]
        allowed.update((i,489) for i in ids)
        allowed.update((i,i+1) for i in ids[:-1])
        # Fix reference to +1. DP retains the last sign and whether - to + occurred.
        dp={(s,False):-2*K[ids[0]][489]*s for s in (-1,1)}
        for i in ids[1:]:
            nxt={}
            for (s,broken),e in dp.items():
                for t in (-1,1):
                    key=(t,broken or s<t)
                    value=e-2*t*(K[i][489]+K[i-1][i]*s)
                    nxt[key]=min(nxt.get(key,value),value)
            dp=nxt
        good,bad=(min(e for (_,broke),e in dp.items() if broke==flag) for flag in (False,True))
        offsets=[]
        for t,cost in enumerate(costs):
            s=[1 if j<t else -1 for j in range(len(ids))]
            e=-2*sum(K[i][489]*x for i,x in zip(ids,s))-2*sum(K[i][i+1]*x*y for i,x,y in zip(ids,s,s[1:]))
            offsets.append(e-4*cost)
        require(len(set(offsets))==1 and good==offsets[0]+4*min(costs),"legal states")
        ground+=good;illegal.append(bad-good);minimum.append(min(costs))
    require(all(K[i][i]==0 for i in range(490)) and max(map(abs,flat))==73,"8-bit scale")
    edges=[]
    for i in range(490):
        for j in range(i+1,490):
            require(K[i][j]==K[j][i] and (not K[i][j] or (i,j) in allowed),"matrix topology")
            if K[i][j]:edges.append((i,j,K[i][j]))
    require(ground==-58722 and min(illegal)==340,"G1 certificate")
    critical=next(b for b in blocks if 226 in b["mapping"])
    require(4*min(q[c] for c in critical["mapping"] if c!=226)==196,"wrong candidate gap")
    return blocks,q,v,candidates,edges,minimum

def decode(s, model):
    blocks,q,v,_,edges,minimum=model
    choices=[];bad=[]
    for b in blocks:
        signs=[x*s[489] for x in s[b["start"]:b["stop"]]]
        bad.append(sum(a<b for a,b in zip(signs,signs[1:])))
        choices.append(b["mapping"][signs.count(1)] if not bad[-1] else None)
    e=-2*sum(k*s[i]*s[j] for i,j,k in edges)
    legal=[c for c in choices if c is not None]
    winner=min(legal,key=lambda c:(q[c],c)) if legal else None
    if not any(bad):
        require(e+58722==4*sum(q[c]-lo for c,lo in zip(choices,minimum)), "energy decomposition")
    return choices,bad,e,winner

def verify(root=HERE):
    manifest=json.loads((root/"sha256.json").read_text())
    for name,h in manifest.items():
        require(digest(root/name)==h, "SHA256 mismatch: "+name)
    model=read_model(root);blocks,q,v,_,_,_=model
    cert=json.loads((root/'matrix_certificate.json').read_text())
    expected=dict(G1='CERTIFIED',G2='CERTIFIED',ground_energy=-58722,illegal_gap=340,
                  batch_candidates=len(q),batch_ground_worst_regret=0,max_J=73,spins=490,
                  matrix_sha256=digest(root/'matrix.npz'),batch_min_value=min(v),global_min_value=min(v))
    require(all(cert[k]==val for k,val in expected.items()), "historical matrix certificate")
    # Boundary witness at exactly 196, other 39 chains locally minimal.
    s=[-1]*489+[1]
    for b in blocks:
        group=b['mapping']; c=min((c for c in group if c!=226),key=lambda c:(q[c],c))
        t=group.index(c);s[b['start']:b['start']+t]=[1]*t
    _,bad,e,c=decode(s,model)
    require(not any(bad) and e+58722==196 and c==448 and v[c]>min(v),"tight witness")
    tasks=read_csv(root/"tasks.csv")
    slots=['P%02d'%i for i in range(1,6)]+['F%02d'%i for i in range(1,21)]
    require([t['slot'] for t in tasks]==slots and len({r['result_id'] for r in tasks})==25,"task mapping")
    audit={r['slot']:r for r in json.loads((root/'return_certificate.json').read_text())['rows']}
    for t in tasks:
        slot=t['slot']; require(t['stage']==('pilot' if slot.startswith('P') else 'formal') and t['status']=='VALID_COMPLETED','stage/status')
        path=root/'returns'/(slot+'.pkl');require(digest(path)==t['source_sha256'],'response hash')
        results=[decode(s,model) for s in spins(path)]
        require(all(not any(bad) for _,bad,_,_ in results),'strict returns')
        es=[r[2] for r in results]; regrets=[v[r[3]]-min(v) for r in results]
        require(all(0 < e+58722 < 196 for e in es) and all(r==0 for r in regrets),slot+' strict envelope')
        a=audit[slot]
        require((min(es),max(es),min(regrets),regrets[es.index(min(es))])==(a['minimum_integer_energy'],a['maximum_integer_energy'],0,0),slot+' aggregate')
        require(len(results)==int(t['returned_set_size'])==a['returns_checked'] and float(t['best_regret_strict'])==min(regrets) and float(t['energy_selected_regret_strict'])==regrets[es.index(min(es))],slot+' service table')
    print('PASS | 529 candidates | 40 chains | 490 spins | G1/G2 CERTIFIED | E0=-58722 | illegal +340 | strict failure +196')
    print('PASS | pilots 5/5 | formal 20/20 | 25 distinct IDs | 250 terminal vectors | energy-selected & best-set strict regret 0')
if __name__=="__main__":verify()
