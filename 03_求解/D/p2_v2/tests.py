"""Meaningful exhaustive contracts, including deliberate certificate errors and failures."""
import itertools
import unittest
import numpy as np
from representation import construct,quantize,legal_energies,metrics
from checker import direct,reconstruct,certify
from task_stats import summarize,cp

class Contracts(unittest.TestCase):
    def test_float_global_equivalence_mask_and_offsets(self):
        for shape in ((2,2),(2,3),(3,3)):
            W=np.arange(np.prod(shape),dtype=float).reshape(shape)/3+2
            for flat in (False,True):
                if flat:W[:]=2
                mask=np.ones(shape,bool);mask[0,-1]=False
                for encoding in ('raw','rc'):
                    J,meta,Q=construct(W,mask,encoding);na,nb=shape
                    states=np.array(list(itertools.product([0,1],repeat=na+nb)))
                    S=np.c_[2*states-1,np.ones(len(states))]
                    energy=-np.sum((S@J)*S,axis=1)+meta['offset']
                    target=np.sum((states@Q)*states,axis=1)+2*meta['lam']
                    np.testing.assert_allclose(energy,target,atol=1e-12)
                    best=np.flatnonzero(np.isclose(energy,energy.min(),atol=1e-12))
                    for idx in best:
                        x=states[idx];self.assertEqual(x[:na].sum(),1);self.assertEqual(x[na:].sum(),1)
                        self.assertTrue(mask[np.argmax(x[:na]),np.argmax(x[na:])])
                    flipped=-S
                    np.testing.assert_allclose(-np.sum((flipped@J)*flipped,axis=1),energy-meta['offset'],atol=1e-12)
    def test_constructed_integer_certificate_and_bounds(self):
        W=np.array([[2.,3.,4.],[5.,6.,7.]])
        mask=np.array([[1,0,1],[0,1,1]],bool)
        for enc in ('raw','rc'):
            J,_,_=construct(W,mask,enc);K,_=quantize(J,16)
            cert=certify(K,mask)
            self.assertEqual(cert['status'],'CERTIFIED',cert)
            states=np.array(list(itertools.product([0,1],repeat=5)))
            E=direct(K,states)
            for r,s,lower in cert.get('cardinality_bounds',[]):
                here=(states[:,:2].sum(axis=1)==r)&(states[:,2:].sum(axis=1)==s)
                self.assertLessEqual(lower,int(E[here].min()))
    def test_integer_checker_against_all_states(self):
        rng=np.random.default_rng(319026)
        for shape in ((2,2),(2,3),(3,3)):
            for _ in range(3):
                n=sum(shape);J=rng.integers(-6,7,size=(n+1,n+1));J=np.triu(J,1);J=J+J.T
                mask=np.ones(shape,bool);mask[0,-1]=False
                states=np.array(list(itertools.product([0,1],repeat=n)));E=direct(J,states)
                c,l,q=reconstruct(J)
                np.testing.assert_array_equal(E,c+states@l+np.sum((states@q)*states,axis=1))
                na,nb=shape;valid=(states[:,:na].sum(axis=1)==1)&(states[:,na:].sum(axis=1)==1)
                for k,x in enumerate(states):
                    if valid[k]:valid[k]=mask[x[:na].argmax(),x[na:].argmax()]
                opt=E[valid].min();truth=E[~valid].min()>opt
                cert=certify(J,mask,seconds=30)
                self.assertEqual(cert['status'],'CERTIFIED' if truth else 'COUNTEREXAMPLE',cert)
                if cert['witness'] is not None:self.assertLessEqual(direct(J,cert['witness'])[0],opt)
    def test_checker_error_and_illegal_tie(self):
        J=np.zeros((5,5),np.int64);mask=np.ones((2,2),bool)
        self.assertEqual(certify(J,mask)['status'],'COUNTEREXAMPLE')
        J[0,1]=1
        self.assertEqual(certify(J,mask)['status'],'IMPLEMENTATION_ERROR')
    def test_top20_and_forbidden(self):
        W=np.arange(30,dtype=float).reshape(5,6);mask=np.ones_like(W,bool);mask[0,0]=False
        E=np.zeros_like(W,dtype=np.int64);keys=np.array([[f'{i}|{j}|NO2' for j in range(6)] for i in range(5)])
        result=metrics(W,mask,E,keys)
        self.assertNotIn(keys[0,0],result['top20_integer']);self.assertEqual(result['ground_count'],29)
        self.assertAlmostEqual(result['top20_min'],11/20);self.assertEqual(result['top20_max'],1.)
    def test_denominators_failures_and_repair(self):
        rows=[dict(slot=f'F{i+1:02d}',status='NOT_STARTED') for i in range(20)]
        self.assertIsNone(summarize(rows)['end_to_end_success'])
        for i,status in enumerate(['SUBMISSION_FAILED','COMPUTATION_FAILED','PENDING','VALID_COMPLETED','VALID_COMPLETED']):rows[i]['status']=status
        rows[1].update(n_feasible=100,best_regret=0.) # Malformed packet must never count.
        rows[3].update(n_feasible=0,n_feasible_repaired=100,best_regret_repaired=.2)
        rows[4].update(n_feasible=1,best_regret=.05,n_feasible_repaired=100,best_regret_repaired=0.)
        raw=summarize(rows);rep=summarize(rows,True)
        self.assertEqual([raw[k] for k in ['N_A','N_V','N_F','N_epsilon']],[5,2,1,1])
        self.assertEqual(raw['G20'][-1]['value'],.05);self.assertEqual(rep['N_F'],2)
        self.assertEqual(raw['slot_success'],.05)
    def test_zero_one_boundaries(self):
        self.assertGreater(cp(0,20)[1],.16);self.assertLess(cp(20,20)[0],.84)
        for success in (False,True):
            rows=[dict(slot=str(i),status='VALID_COMPLETED',n_feasible=int(success),best_regret=0. if success else None) for i in range(20)]
            result=summarize(rows);self.assertEqual(result['bootstrap_boundary'],'all_one' if success else 'all_zero')

if __name__=='__main__':unittest.main(verbosity=2)
