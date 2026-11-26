"""Non-training contract tests; library parity is separately counted."""
import json
import unittest
import numpy as np
import pandas as pd
from common import OUT,load_data,fold_ids,Budget
from metrics import evaluate,ordered
from models import Factory


class Contracts(unittest.TestCase):
    def test_group_isolation_and_order(self):
        g=np.array(['A|B','B|A','A|B','C|D','D|C'])
        f=fold_ids(g,3,'unit');self.assertEqual(f[0],f[2])
        np.testing.assert_array_equal(f[::-1],fold_ids(g[::-1],3,'unit'))

    def test_event_and_mse_decomposition(self):
        d=pd.DataFrame(dict(V=[0.,2.,2.001,10.],gap=[1.,1.,1.,0.],ab=['a','b','c','d'],key=['a','b','c','d']))
        v=np.array([1.,2.,3.,8.]);r=evaluate(d,dict(score=-v,vhat=v,vhat_raw=v))
        self.assertEqual(r['M'],2);self.assertAlmostEqual(r['EF@20'],1.)
        self.assertAlmostEqual(r['RMSE']**2,r['metal_MSE_contribution']+r['nonmetal_MSE_contribution'])
        d.V=[3.,4.,5.,10.];self.assertTrue(np.isnan(evaluate(d,dict(score=-v))['EF@20']))

    def test_ties_do_not_depend_on_row_order(self):
        keys=np.array(['b','a','c']);s=np.ones(3)
        self.assertEqual(list(keys[ordered(s,keys)]),list(keys[::-1][ordered(s,keys[::-1])]))

    def test_feature_masks_and_forbidden_inputs(self):
        tags=json.loads((OUT/'feature_schema.json').read_text())
        for feature,tag in [('F3','E1'),('minus_electronic','electronic'),('minus_geometry','geometry'),('minus_xstats','xstats')]:
            cols=pd.read_pickle(OUT/'features'/(feature+'.pkl')).columns
            self.assertTrue(all(tag not in tags[c] for c in cols))
        cols=pd.read_pickle(OUT/'features/F4.pkl').columns
        forbidden={'gap','V','e_form','a_lat','volume','vbm','cbm','mu_b','fermi_level','fermi_width','id'}
        self.assertFalse(set(cols)&forbidden)

    def test_training_scope_rejects_eval_before_fitting(self):
        d=load_data('02',True).iloc[:5]
        X=pd.DataFrame({'f':np.ones(5)})
        f=Factory(d,X,'unit','unit',[0,1,2],[3,4]);before=Budget().count()
        with self.assertRaises(AssertionError):f.fit([0,3],'raw')
        self.assertEqual(before,Budget().count())


if __name__=='__main__':unittest.main()
