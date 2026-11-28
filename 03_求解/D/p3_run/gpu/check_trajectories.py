"""Cross-check production CUDA state transitions against direct dense enumeration."""
import json
import numpy as np
import torch
from scipy.sparse import csr_matrix
from gpu_runner import Kernel, OUT, device

MASK=(1<<64)-1
def draw(state):
    state ^= state>>12
    state ^= (state<<25)&MASK
    state ^= state>>27
    return state,(state*0x2545F4914F6CDD1D)&MASK

def test(kernel,n):
    matrix=np.zeros((n,n),dtype=np.int32)
    for i in range(n-2):
        if n==8 and i==3: continue
        matrix[i,i+1]=3 if i%2==0 else -2
    for i in range(n-1): matrix[i,-1]=[1,-3,2][i%3]
    matrix+=matrix.T.copy()
    m=1<<n
    signs=(2*((np.arange(m)[:,None]>>np.arange(n))&1)-1).astype('int8')
    best=signs.copy()
    energies=-np.einsum('bi,ij,bj->b',signs,matrix,signs)
    bs=energies.copy()
    rng=[7890004+i for i in range(m)]
    csr=csr_matrix(matrix)
    csr_buffers=[device(arr.astype('int32')) for arr in (csr.indptr,csr.indices,csr.data)]
    levels=[32.,8.,2.]
    levels_d=device(np.array(levels))
    args=[device(np.array(rng,dtype='uint64')),device((signs@matrix).T.copy()),
          device(signs.T.copy()),device(best.T.copy()),device(energies),device(bs)]
    for t,temp in enumerate(levels):
        kernel.launch('cool',m,[m,n,t,t+1,levels_d,*csr_buffers,*args])
        for a in range(m):
            for _ in range(n):
                r,v=draw(rng[a])
                while v<((1<<64)-n)%n: r,v=draw(r)
                site=v%n
                r,u=draw(r)
                rng[a]=r
                trial=signs[a].copy()
                trial[site]*=-1
                en=-int(trial@matrix@trial)
                d=en-int(energies[a])
                if d>0 and (u>>11)/2**53>=np.exp(-d/temp): continue
                signs[a]=trial
                energies[a]=en
                if en<bs[a]: bs[a]=en;best[a]=trial
        wanted=[np.array(rng,dtype='uint64'),(signs@matrix).T,signs.T,best.T,energies,bs]
        for real,want in zip(args,wanted):
            np.testing.assert_array_equal(real.cpu().numpy(),want)
    return dict(n=n,starting_states=m,temperature_levels=levels,matched_fields=['rng','local_field','current_vector','best_vector','current_energy','best_energy'],checked_sweeps=m*len(levels),checked_proposals=m*n*len(levels))

if __name__=='__main__':
    kern=Kernel()
    results=[test(kern,n) for n in (5,8)]
    with (OUT/'production_trace_checks.json').open('x') as f:
        json.dump(results,f,indent=2)
