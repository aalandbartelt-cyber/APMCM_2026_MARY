"""Independent code-path checks; reads only archived / synthetic signed vectors."""
from pathlib import Path
import unittest
import numpy as np
import replay_cloud as replay


class IndependentReplayTest(unittest.TestCase):
    def compare(self, family, batch, spins, cert):
        result = replay.evaluate(batch, spins, cert)
        frozen = replay.protocol.judge_return(family, batch, spins)
        self.assertEqual(result, {key:frozen[key] for key in result})
        return result

    def test_illegal_partial_and_tied_earliest_vector_each_family(self):
        certificates = replay.read(replay.SEAL/"certificates.json")["batches"]
        for family in replay.protocol.SLICES:
            with self.subTest(family=family), np.load(replay.SEAL/f"{family}.npz", allow_pickle=False) as batch:
                v = batch["witnesses"][0]
                broken = v.copy()
                broken[:2] = [-v[-1], v[-1]]
                got = self.compare(family, batch, np.stack([broken, -v, v]), certificates[family])
                self.assertEqual(got["rows"][0]["invalid_groups"], [1])
                self.assertIn("partial_only", got["rows"][0])
                self.assertEqual(got["primary"]["return_index"], 1)

    def test_all_available_p2_formal_archive_data(self):
        base = replay.ROOT / "artifacts/p2_cim_go_20261128/service_audit"
        if not base.is_dir():
            self.skipTest("P2 private archive unavailable")
        cert = replay.read(replay.SEAL/"certificates.json")["batches"]["NO2"]
        paths = sorted(base.glob("F*/result.pkl"))
        self.assertEqual(len(paths), 20)
        n = 0
        with np.load(replay.SEAL/"NO2.npz", allow_pickle=False) as batch:
            for path in paths:
                spins = replay.ordered_spins(path.read_bytes())
                np.testing.assert_array_equal(spins, np.load(path.with_name("spins.npy"), allow_pickle=False))
                self.compare("NO2", batch, spins, cert)
                n += len(spins)
        self.assertEqual(n, 200)
