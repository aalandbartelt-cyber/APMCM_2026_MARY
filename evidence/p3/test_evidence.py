"""Offline regression tests on copies of sealed evidence and an isolated Git history."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p3_independent_verify", HERE / "verify.py")
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class WitnessFaults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with np.load(HERE / "O3.npz", allow_pickle=False) as z:
            cls.data = {k: z[k] for k in z.files}

    def reject_field(self, key, value, reason):
        with self.assertRaisesRegex(ValueError, reason):
            verify.audit_batch({**self.data, key: value}, "O3")

    def test_unsigned_reference_outside_matrix(self):
        self.reject_field("reference", np.array(np.iinfo(np.uint64).max, "u8"), "reference")

    def test_duplicate_official_candidate(self):
        ids = self.data["ids"].copy()
        ids[1] = ids[0]
        self.reject_field("ids", ids, "dictionary")

    def test_mapping_not_an_ordered_bijection(self):
        mapping = self.data["mapping"].copy()
        mapping[2] = mapping[1]
        self.reject_field("mapping", mapping, "bijection")

    def test_group_boundary_off_by_one(self):
        offsets = self.data["offsets"].copy()
        offsets[1] -= 1
        self.reject_field("offsets", offsets, "segmentation")

    def test_false_finite_distance(self):
        d = self.data["D"].copy()
        d[np.flatnonzero(d == -1)[0]] = 0
        self.reject_field("D", d, "lower bound")

    def test_false_unreachable(self):
        d = self.data["D"].copy()
        d[np.flatnonzero(d >= 0)[0]] = -1
        self.reject_field("D", d, "lower bound")

    def test_wrong_candidate_position_in_witness_index(self):
        index = self.data["witness_index"].astype("uint64")
        index[0] = np.iinfo("uint64").max
        self.reject_field("witness_index", index, "witness index")

    def test_witness_one_spin_flip(self):
        s = self.data["witnesses"].copy()
        # Flip a spin in the interior of a constant-sign run of the first chain.
        n = int(self.data["offsets"][1]) - 1
        row = s[0, :n]
        j = 1 + np.flatnonzero((row[:-2] == row[1:-1]) & (row[1:-1] == row[2:]))[0]
        s[0, j] *= -1
        self.reject_field("witnesses", s, "illegal spin transition")

    def test_legal_witness_of_wrong_candidate(self):
        s = self.data["witnesses"].copy()
        s[[0, 1]] = s[[1, 0]]
        self.reject_field("witnesses", s, "wrong candidate")

    def test_gauge_equivalent_witness_passes(self):
        s = self.data["witnesses"].copy()
        s[0] *= -1
        out = verify.audit_batch({**self.data, "witnesses": s}, "O3")
        self.assertEqual(out["reachable"], 281)


class ExportFaults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = {}
        for name in verify.MATRIX_SHA:
            with np.load(HERE / (name + ".npz"), allow_pickle=False) as data:
                cls.reports[name] = verify.audit_batch(data, name)

    def reject_edit(self, filename, column, value, message):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in verify.MATRIX_SHA:
                (folder / (name + ".npz")).symlink_to(HERE / (name + ".npz"))
            for name in ("candidates.csv", "envelopes.csv"):
                if name != filename:
                    (folder/name).symlink_to(HERE/name)
                    continue
                with (HERE/name).open(newline="", encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                self.assertNotEqual(rows[0][column], value)
                rows[0][column] = value
                with (folder/name).open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
                    writer.writeheader()
                    writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, message):
                verify.audit_exports(folder, self.reports)

    def test_envelope_height_tamper(self):
        self.reject_edit("envelopes.csv", "max_regret", "0.0000000000000001", "exact bound")

    def test_csv_wrong_official_id(self):
        self.reject_edit("candidates.csv", "id", "-1", "dictionary CSV")


class FirstReceiptAnchor(unittest.TestCase):
    def test_deleted_receipt_cannot_be_reissued(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def git(*args):
                return subprocess.check_output(
                    ["git", "-C", str(root), "-c", "user.name=Test",
                     "-c", "user.email=fixture@invalid", "-c", "commit.gpgsign=false", *args]
                ).decode().strip()

            git("init", "-q")
            files = {}
            names = [n + ".npz" for n in verify.MATRIX_SHA]
            names += ["verify.py", "protocol.py", "test_protocol.py", "candidates.csv", "envelopes.csv"]
            paths = [verify.PACK/n for n in names] + [Path("codex/P3_FINAL.md")]
            for path in paths:
                f = root/path
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(b"test-only synthetic anchor fixture\n")
                files[path.as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
            receipt = root/verify.RECEIPT
            original = json.dumps({"files": files, "revision": 1})
            receipt.write_text(original)
            git("add", "-f", ".")
            git("commit", "-qm", "First receipt")
            first = git("rev-parse", "HEAD")
            self.assertEqual(verify.verify_anchor(root, root, first)[0], first)
            git("rm", "-q", verify.RECEIPT.as_posix())
            git("commit", "-qm", "Delete receipt")
            receipt.write_text(json.dumps({"files": files, "revision": 2}))
            git("add", verify.RECEIPT.as_posix())
            git("commit", "-qm", "Recreate receipt")
            later = git("rev-parse", "HEAD")
            with self.assertRaisesRegex(ValueError, "full first commit SHA"):
                verify.verify_anchor(root, root, later)
            with self.assertRaisesRegex(ValueError, "differs from first Git anchor"):
                verify.verify_anchor(root, root, first)
            with self.assertRaisesRegex(ValueError, "differs from first Git anchor"):
                verify.verify_anchor(root, root)


if __name__ == "__main__":
    unittest.main()
