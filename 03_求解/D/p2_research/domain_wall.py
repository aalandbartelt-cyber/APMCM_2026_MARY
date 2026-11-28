"""Exploratory joint-candidate domain wall; no SDK or hardware dependency."""
from pathlib import Path
import json, hashlib, itertools
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/p2_research_20261128/domain_wall'

def build(q, levels=127):
    """Pad endpoint values, then represent the unary cost on a prefix chain."""
    q = np.asarray(q, dtype=np.int64)
    assert q.ndim == 1 and len(q) >= 2 and q.min() >= 0 and q.max() <= levels
    padded = np.r_[q[0], q, q[-1]]
    n = len(padded) - 1
    # P is an even integer strictly larger than the cost range.
    P = 2 * (levels // 2 + 1)
    K = np.zeros((n + 1, n + 1), dtype=np.int64)
    ids = np.arange(n - 1)
    K[ids, ids + 1] = K[ids + 1, ids] = P // 2
    fields = -np.diff(padded)
    fields[0] += P // 2
    fields[-1] -= P // 2
    K[:n, n] = K[n, :n] = fields
    assert np.abs(K).max() <= levels
    return K, padded, P

def polynomial(q, P, x):
    return int(q[0] + np.diff(q) @ x + P * np.sum(x[1:] * (1 - x[:-1])))

def tiny_exhaustive():
    rng = np.random.default_rng(2026112801)
    counts = 0
    for m in range(2, 8):
        for trial in range(12):
            q = rng.integers(0, 128, size=m)
            K, padded, P = build(q)
            offset = int(-np.r_[-np.ones(len(K)-1,dtype=int),1] @ K @ np.r_[-np.ones(len(K)-1,dtype=int),1] - 4*padded[0])
            allowed = []; forbidden = []
            for bits in itertools.product([0,1],repeat=len(K)-1):
                x=np.array(bits);s=np.r_[2*x-1,1];e=int(-s@K@s)
                assert e == 4*polynomial(padded,P,x)+offset
                (forbidden if np.any(x[1:]>x[:-1]) else allowed).append(e)
                counts+=1
            assert min(forbidden)>min(allowed)
    return counts

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    registration = dict(experiment='DW01',purpose='existence construction and exact certification before sampling',
        order='original axis order; row-major allowed pairs; no cost sorting',
        quantization='nearest even integer of 127*(W-min)/(max-min)',
        levels=127,P=128,endpoint_padding='duplicate first and last candidate costs',
        new_fits=0,hardware_calls=0)
    with (OUT/'DW01_registration.json').open('x') as f:json.dump(registration,f,indent=2)
    count=tiny_exhaustive()
    z=np.load(ROOT/'artifacts/p23_v2/pool_11.npz');W=z['vhat'][:,:,0];mask=z['allowed'][:,:,0]
    ij=np.argwhere(mask);values=W[mask];vmin=float(values.min());R=float(np.ptp(values))
    q=np.rint(127*(values-vmin)/R).astype(np.int64)
    K,padded,P=build(q);mapping=np.r_[0,np.arange(len(values)),len(values)-1]
    file=OUT/'DW01_11_joint.npz'
    with file.open('xb') as f:np.savez_compressed(f,J=K,q=padded,candidate_indices=ij,mapping=mapping,values=values)
    report=dict(tiny_states_checked=count,original_candidates=len(values),padded_states=len(padded),
        physical_spins=len(K),max_abs_coefficient=int(np.abs(K).max()),nonzero_edges=int(np.count_nonzero(K)//2),
        quantization_step=R/127,max_cost_error=float(np.abs(vmin+q*R/127-values).max()),
        quantized_ground_candidates=int(np.sum(q==q.min())),ground_worst_regret=float(values[q==q.min()].max()-vmin),
        R=R,minimum=vmin,second_gap=float(np.sort(values)[1]-vmin),
        matrix_file=str(file.relative_to(ROOT)),file_sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    with (OUT/'DW01_build.json').open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
