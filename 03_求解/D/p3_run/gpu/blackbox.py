"""Single-proposal public SDK diagnostic using a fresh solver per prescribed seed."""
import json
import socket
from collections import Counter
from pathlib import Path
import numpy as np
import kaiwu as kw
from scipy.stats import binomtest

def no_network(*args,**kwargs):
    raise RuntimeError('Offline gate')
socket.socket.connect=no_network
out=Path(__file__).resolve().parents[4]/'artifacts/p3_run/B/gpu_gate'
states=Counter()
histories=Counter()
J=np.array([[0.,1.],[1.,0.]])
for seed in range(7901000,7902000):
    sa=kw.classical.SimulatedAnnealingOptimizer(initial_temperature=4.,cutoff_temperature=3.,
        alpha=.5,iterations_per_t=1,size_limit=10,rand_seed=seed,process_num=1,flag_evolution_history=True)
    arr=sa.single_process_solve(ising_matrix=J,init_solution=np.array([1.,1.]),rand_seed=seed)
    states[str(np.asarray(arr).astype(int).tolist())]+=1
    histories[tuple(float(v) for v in sa.get_ha_history().values())]+=1
assert set(histories)<= {(-2.,),(-2.,2.)}
pf=histories[(-2.,2.)]/1000
iv=binomtest(histories[(-2.,2.)],1000).proportion_ci()
with (out/'cpu_one_proposal.json').open('x') as f:
    json.dump(dict(T=4,attempts=1000,J12=1,start=[1,1],theoretical_uphill=np.exp(-4/4),
                   public_history_ending_at_uphill=pf,ci95=[iv.low,iv.high],
                   returned_solution_collections=dict(states),ordered_history_energy_patterns={str(k):v for k,v in histories.items()},
                   caveat='These are tiny one-proposal SDK energy histories & solution collections. Site selection and unobserved queue policy remain unknown.'),f,indent=2)
