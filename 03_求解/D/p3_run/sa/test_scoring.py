"""Offline checks of prefix tie handling, strict filtering and independent decoding."""
import unittest

import numpy as np

from register import ROOT, FAMILIES
from score import primary_for, independent_decode, sealed_scorer


class FormalRules(unittest.TestCase):
    def test_prefix_ignores_lower_nonstrict_and_later_exact_tied_energy(self):
        rows=[
            dict(status='SCORED',strict=False,energy=-10,restart=1,exact=None),
            dict(status='SCORED',strict=True,energy=-4,restart=2,exact=False),
            dict(status='SCORED',strict=True,energy=-4,restart=3,exact=True),
        ]
        self.assertIsNone(primary_for(rows[:1]))
        self.assertIsNone(primary_for([]))
        self.assertEqual(primary_for(rows)['restart'],2)
        rows.append(dict(status='SCORED',strict=True,energy=-8,restart=4,exact=True))
        self.assertEqual(primary_for(rows)['restart'],4)

    def test_known_walls_and_gauge(self):
        protocol=sealed_scorer()
        for f in FAMILIES:
            with np.load(ROOT/'evidence/p3'/(f+'.npz'),allow_pickle=False) as source:
                data={k:source[k] for k in source}
            illegal=np.ones(490,dtype=np.int8)
            illegal[1]=-1
            probes=[illegal]
            for s in data['witnesses'][::20]:
                probes.extend((s,-s))
            for s in probes:
                row=protocol.judge_return(f,data,s[None,:])['rows'][0]
                energy,invalid,choice=independent_decode(data,s)
                self.assertEqual(energy,row['energy'])
                self.assertEqual(invalid,row['invalid_groups'])
                self.assertEqual(choice is not None,row['strict'])
                if choice:
                    self.assertTrue(all(row[k]==v for k,v in choice.items()))


if __name__=='__main__':
    unittest.main()
