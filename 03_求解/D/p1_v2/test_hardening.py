"""Numerical contract tests for postprocessing, with no fitting or real labels."""
import unittest
import numpy as np
import pandas as pd
from report import cluster_bootstrap, frequency_ef, summary_metrics
from hardening_tables import build_main_tables
from decision_stability import decision_pair, concentration, choose_construction


class BootstrapTests(unittest.TestCase):
    def test_frequency_matches_literal_duplicates_and_undefined_event(self):
        gid = np.array([0, 0, 0, 1, 1, 1])
        y = np.array([1, 0, 1, 0, 0, 0], bool)
        order = np.array([3, 0, 4, 1, 5, 2])
        counts = np.array([[2, 0], [0, 2], [1, 1], [0, 4]])
        ef, N = frequency_ef(counts, gid, y, order, k=3)
        for i, count in enumerate(counts):
            duplicated = np.repeat(order, count[gid[order]])
            truth = y[duplicated]
            expected = truth[:3].mean()/truth.mean() if truth.any() else np.nan
            np.testing.assert_allclose(ef[i], expected, equal_nan=True)
            self.assertEqual(N[i], len(duplicated))

    def fixture(self):
        rows = []
        for fold in range(2):
            for j in range(40):
                rows.append(dict(key=f'{fold}:{j:02}', ab=f'{fold}:{j//10}', outer_fold=fold,
                                 V=1. if j<10 else 4., vhat=2. if j<10 else 3.,
                                 score=-j if fold == 0 else j-100))
        a = pd.DataFrame(rows)
        b = a.copy(); b['score'] = -np.arange(len(b))
        return {'a': a, 'b': b}

    def test_macro_point_and_fold_scale_invariance(self):
        frames = self.fixture()
        out = cluster_bootstrap(frames, [('a', 'b')], n=100)
        ef = out[out.metric == 'EF_macro@20'].iloc[0]
        self.assertAlmostEqual(ef.delta_point, -1.)
        # Both pooled rankings choose exactly the same first-fold Top-20.
        self.assertNotEqual(ef.delta_point, 0.)
        shifted = {k: v.copy() for k, v in frames.items()}
        shifted['a'].loc[shifted['a'].outer_fold == 1, 'score'] += 1000
        rescaled = cluster_bootstrap(shifted, [('a', 'b')], n=100)
        pd.testing.assert_frame_equal(out, rescaled)
        self.assertLess(ef.n_valid, 100)  # Any undefined fold invalidates the macro.

    def test_crossed_group_rejected(self):
        frames = self.fixture()
        frames['a']['ab'] = frames['a']['ab'].str[-1]
        with self.assertRaises(AssertionError):
            cluster_bootstrap(frames, [('a', 'b')], n=2)


class DecisionTests(unittest.TestCase):
    def test_cross_table_regret_and_overlap(self):
        a = np.array([0., .01, 8., 9.]); b = np.array([.02, 0., 9., 8.])
        result = decision_pair(a, b, np.argsort(a), np.argsort(b), k=2)
        np.testing.assert_allclose(result, [0, 1, 1, .015])

    def test_concentration_uses_pool_denominator(self):
        out = concentration(['x', 'x', 'x', 'y'], [0, 1])
        self.assertEqual(out['HHI'], 1)
        self.assertAlmostEqual(out['dominant_share_over_pool_share'], 4/3)

    def test_policy_requires_every_condition(self):
        rows = []
        for p in ['07', '08', '11', '12']:
            for method, agree, overlap, regret in [('single_member', .2, .5, .2), ('bagged_half10', .3, .6, .1)]:
                rows.append(dict(pool=p, method=method, argmin_agreement=agree,
                    top20_overlap_fraction=overlap, top20_jaccard=overlap/(2-overlap),
                    symmetric_cross_table_decision_regret=regret))
        d = pd.DataFrame(rows); protocol = {'selection_rule': {'numeric_tolerance': 1e-12}}
        self.assertEqual(choose_construction(d, protocol)['construction'], 'bagged_mean_20')
        d.loc[(d.pool=='12') & (d.method=='bagged_half10'), 'symmetric_cross_table_decision_regret'] = .3
        self.assertEqual(choose_construction(d, protocol)['construction'], 'single_full_fit')

    def test_table_uses_weighted_sse_and_keeps_selection_identity(self):
        rows, nested = [], []
        for f in range(5):
            r = dict(protocol='outer', domain=f'main_outer_{f}', route='a', feature_set='F4',
                     N=40+f, M=4, n_metal=20, n_nonmetal=20+f, RMSE=1+f,
                     MAE=1, **{'EF@20': (2/20)/(4/(40+f)), 'hits@20': 2})
            rows.append(r)
            rows.append(dict(r, protocol='baseline', domain=f'baseline_{f}', route='mean'))
            nested.append(dict(fold=f, numeric='a', screen='a', numeric_result=r, screen_result=r))
        main, detail = build_main_tables(pd.DataFrame(rows), nested, summary_metrics)
        expected = np.sqrt(np.average(np.arange(1,6)**2, weights=np.arange(40,45)))
        np.testing.assert_allclose(main.RMSE, expected)
        self.assertEqual(len(detail), 20)
        self.assertEqual(set(detail[detail.route == 'nested_screen'].selection_identity), {'a'})


if __name__ == '__main__':
    unittest.main()
