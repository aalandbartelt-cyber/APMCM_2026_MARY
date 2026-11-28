"""Inject faults into temporary copies, leaving all certified inputs byte-identical."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

from validation_checker import BASE, certify
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'evidence/p2'))
from verify import HERE, verify, validate_mapping

def require_rejection(fn):
    try:
        fn()
    except (AssertionError, ValueError) as exc:
        return type(exc).__name__
    raise RuntimeError('A faulty fixture passed')

def main():
    rows=[]
    with tempfile.TemporaryDirectory() as temp:
        dest=Path(temp)/'40_real'
        dest.mkdir()
        src=BASE/'short_H05/40_real'
        shutil.copyfile(src/'matrix.npz',dest/'matrix.npz')
        # Use the registered business matrix with repeated q values. An equal-q
        # duplicate passes all per-chain energy checks, exercising coverage itself.
        import numpy as np
        q=np.load(dest/'matrix.npz')['q']
        for fault in ('missing','duplicate_equal_q','out_of_range','wrong_reference'):
            blocks=json.loads((src/'blocks.json').read_text())
            b=blocks[0]
            if fault=='missing': b['mapping'].pop()
            elif fault=='duplicate_equal_q':
                i=b['mapping'][0]
                b['mapping'][0]=next(j for j,x in enumerate(q) if x==q[i] and j!=i)
            elif fault=='out_of_range': b['mapping'][0]=529
            elif fault=='wrong_reference': b['reference']=488
            (dest/'blocks.json').write_text(json.dumps(blocks))
            rows.append(dict(fault=fault,checker=require_rejection(lambda:certify(dest)),offline=require_rejection(lambda:validate_mapping(blocks,529,489))))
        perm=BASE/'validation_H07_H08/blind_permutation_real'
        c=certify(perm)
        require=c['G1']==c['G2']=='CERTIFIED' and c['mapped_candidates']!=list(range(529))
        if not require:raise RuntimeError('Valid permutation fixture')
        rows.append(dict(fault='authentic_permuted_dictionary',checker='PASS',offline='PASS'))
        validate_mapping(json.loads((perm/'blocks.json').read_text()),529,489)
        clone=Path(temp)/'evidence';shutil.copytree(HERE,clone)
        p=clone/'returns/F14.pkl';raw=bytearray(p.read_bytes());raw[-7]^=1;p.write_bytes(raw)
        rows.append(dict(fault='one_payload_byte',checker='N/A',offline=require_rejection(lambda:verify(clone))))
    with contextlib.redirect_stdout(io.StringIO()):verify()
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
