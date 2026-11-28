"""CUDA-side qualification of independent, serial single-site SA replicas."""
import hashlib
import inspect
import itertools
import json
import math
from pathlib import Path
import numpy as np
import torch
from cuda.bindings import driver, nvrtc
from scipy.sparse import csr_matrix

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=ROOT/'artifacts/p3_run/B/gpu_gate'
REG=json.loads((OUT/'preregistration.json').read_text())

def success(result):
    status,*values=result
    if int(status)!=0:
        raise RuntimeError(f'CUDA call returned {status}')
    return values[0] if len(values)==1 else values

class Kernel:
    def __init__(self):
        torch.cuda.init()
        torch.empty(0,device='cuda')
        raw=(HERE/'serial_sa.cu').read_bytes()
        self.program=success(nvrtc.nvrtcCreateProgram(raw,b'serial_sa.cu',0,[],[]))
        opts=[b'--gpu-architecture=compute_120', b'--std=c++14']
        compiled=nvrtc.nvrtcCompileProgram(self.program,len(opts),opts)
        log=bytearray(success(nvrtc.nvrtcGetProgramLogSize(self.program)))
        success(nvrtc.nvrtcGetProgramLog(self.program,log))
        if int(compiled[0]):
            raise RuntimeError(f'Compile failure: {bytes(log).decode()}')
        ptx=bytearray(success(nvrtc.nvrtcGetPTXSize(self.program)))
        success(nvrtc.nvrtcGetPTX(self.program,ptx))
        self.module=success(driver.cuModuleLoadData(np.frombuffer(ptx,dtype=np.uint8).ctypes.data))
        self.funcs={x:success(driver.cuModuleGetFunction(self.module,x.encode())) for x in
                    ('prepare','cool','verify_move')}

    def launch(self,name,m,args):
        packed=[np.array(v,dtype=np.int32) if isinstance(v,int)
                else np.array(v.data_ptr(),dtype=np.uint64) for v in args]
        ptrs=np.array([v.ctypes.data for v in packed],dtype=np.uintp)
        stream=driver.CUstream(torch.cuda.current_stream().cuda_stream)
        success(driver.cuLaunchKernel(self.funcs[name],(m+31)//32,1,1,32,1,1,0,stream,ptrs.ctypes.data,0))

def device(x):
    return torch.as_tensor(np.ascontiguousarray(x),device='cuda')

def exact_check(kernel):
    reports=[]
    for n in (5,8):
        dense=np.zeros((n,n),dtype=np.int32)
        for i in range(n-2):
            if n==8 and i==3: continue
            dense[i,i+1]=3 if i%2==0 else -2
        for i in range(n-1):
            dense[i,-1]=[1,-3,2][i%3]
        dense+=dense.T.copy()
        rows=np.array(list(itertools.product(range(2**n),range(n),(0.5,4.0,23.0),
                                             (0.0001,0.19,0.63,0.99))))
        seq,site=rows[:,:2].T.astype(np.int32)
        T,u=rows[:,2:].T
        sign=2*((seq[:,None]>>np.arange(n))&1)-1
        flip=sign.copy()
        flip[np.arange(len(seq)),site]*=-1
        energy=-np.einsum('bi,ij,bj->b',sign,dense,sign)
        new=-np.einsum('bi,ij,bj->b',flip,dense,flip)
        delta=new-energy
        accepted=(delta<=0)|(u<np.exp(-np.maximum(delta,0)/T))
        final=np.where(accepted,seq^(1<<site),seq)
        args=[device(x) for x in (dense,seq,site,T,u)]
        output=[torch.empty(len(seq),dtype=torch.int32,device='cuda') for _ in range(3)]
        kernel.launch('verify_move',len(seq),[len(seq),n,*args,*output])
        got=[v.cpu().numpy() for v in output]
        mismatch=[int(np.count_nonzero(g!=w)) for g,w in zip(got,(energy,delta,final))]
        reports.append(dict(spins=n,states=2**n,moves=len(seq),energy_errors=mismatch[0],
                            increment_errors=mismatch[1],transition_errors=mismatch[2]))
    return reports

def run_vectors(kernel,matrix,seeds):
    m,n=len(seeds),len(matrix)
    compressed=csr_matrix(matrix.astype(np.int32))
    csr=[device(arr.astype(np.int32)) for arr in (compressed.indptr,compressed.indices,compressed.data)]
    seeds_d=device(np.array(seeds,dtype=np.int64))
    rng=torch.empty_like(seeds_d)
    h=torch.empty((n,m),dtype=torch.int32,device='cuda')
    s=torch.empty((n,m),dtype=torch.int8,device='cuda')
    best=torch.empty_like(s)
    energy=torch.empty(m,dtype=torch.int32,device='cuda')
    best_e=torch.empty_like(energy)
    state=[*csr,rng,h,s,best,energy,best_e]
    kernel.launch('prepare',m,[m,n,seeds_d,*state])
    levels=[]
    temp=4.0*np.abs(matrix.astype(np.int64)).sum(1).max()
    while temp>REG['cutoff_absolute']:
        levels.append(temp)
        temp*=REG['alpha']
    temperature=device(np.array(levels,dtype=np.float64))
    for lo in range(0,len(levels),16):
        kernel.launch('cool',m,[m,n,lo,min(lo+16,len(levels)),temperature,*state])
    vectors=best.cpu().numpy().T.copy()
    vectors*=vectors[:,-1:].copy()
    energies=-np.einsum('bi,ij,bj->b',vectors,matrix.astype(np.int64),vectors)
    np.testing.assert_array_equal(energies,best_e.cpu().numpy())
    return vectors,dict(steps=len(levels),start=levels[0],last=levels[-1],flips=len(levels)*n)

if __name__=='__main__':
    kernel=Kernel()
    tests=exact_check(kernel)
    with (OUT/'exact_steps.json').open('x') as out:
        json.dump(tests,out,indent=2)
    assert all(record['energy_errors']==record['increment_errors']==record['transition_errors']==0 for record in tests)
    schedules={}
    with (OUT/'gpu_vectors.jsonl').open('x') as sink:
        for j,family in enumerate(REG['families']):
            mat=np.load(ROOT/'evidence/p3'/f'{family}.npz')['J']
            assert hashlib.sha256(mat.astype('<i8').tobytes()).hexdigest()==REG['matrix_sha_i64'][family]
            seeds=[660001+1000*j+i for i in range(REG['n_per_family'])]
            vectors,schedules[family]=run_vectors(kernel,mat,seeds)
            for seed,vec in zip(seeds,vectors):
                sink.write(json.dumps(dict(family=family,seed=seed,vector=vec.tolist()),separators=(',',':'))+'\n')
            sink.flush()
    with (OUT/'schedules.json').open('x') as out: json.dump(schedules,out,indent=2)
