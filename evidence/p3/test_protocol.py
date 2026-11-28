"""Regression fixtures for frozen service adjudication (no SDK, account or network)."""
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np

import protocol as p


HERE = Path(__file__).resolve().parent


def witness(data, c):
    i = int(np.flatnonzero(data["witness_index"] == c)[0])
    return data["witnesses"][i].astype(np.int64).copy()


def select_witnesses(data):
    win = int(np.argmin(data["values"]))
    reachable = data["witness_index"]
    wrong = min((i for i in reachable if i != win), key=lambda i: data["D"][i])
    hit = witness(data, win)
    high_hit = hit.copy()
    for g, (a, b) in enumerate(zip(data["offsets"][:-1], data["offsets"][1:])):
        if a <= win < b:
            continue
        length = b - a - 1
        choice = int(np.argmax(data["q"][a:b]))
        high_hit[a-g:b-g-1] = np.where(np.arange(length) < choice, 1, -1) * hit[-1]
    return hit, witness(data, wrong), high_hit


def bill(before=11):
    return {"before": {"550": before, "1000": 2}, "after": {"550": before-1, "1000": 2},
            "attributable": True}


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {}
        cls.outcomes = {}
        for family in p.SLICES:
            with np.load(HERE / (family + ".npz"), allow_pickle=False) as data:
                cls.data[family] = dict(data)
            d = cls.data[family]
            hit, wrong, _ = select_witnesses(d)
            two_partial = np.stack([hit, hit])
            for g in range(2):
                a = d["offsets"][g] - g
                two_partial[g, a:a+2] = np.array([-1, 1]) * hit[-1]
            cls.outcomes[family] = {
                "hit": p.judge_return(family, d, [hit]),
                "miss": p.judge_return(family, d, [wrong]),
                "no_strict": p.judge_return(family, d, two_partial)}

    def record(self, slot, kind="hit", status="VALID_COMPLETED"):
        family = p.FAMILY[slot]
        record = {"family": family, "status": status, "task_id": f"offline-{slot}",
                  "billing": bill(12-int(slot[1:]))}
        if status == "VALID_COMPLETED":
            record["outcome"] = self.outcomes[family][kind]
        return record

    def test_minimum_integer_energy_is_primary(self):
        for f in p.SLICES:
            hit, wrong, high_hit = select_witnesses(self.data[f])
            res = p.judge_return(f, self.data[f], [high_hit, wrong])
            self.assertEqual(res["status"], "VALID_COMPLETED")
            self.assertGreater(res["rows"][0]["energy"], res["rows"][1]["energy"])
            self.assertEqual(res["primary"]["return_index"], 1)
            self.assertFalse(res["primary"]["exact"])
            self.assertEqual(res["secondary"], {"exists_strict_hit": True, "min_strict_regret": 0})
            self.assertEqual(p.judge_return(f, self.data[f], [-hit])["primary"]["regret"], 0)

    def test_energy_tie_keeps_original_position_despite_regret(self):
        d = self.data["O3"]
        groups = {}
        for i in d["witness_index"]:
            e = int(d["D"][i])
            if e in groups and d["values"][i] != d["values"][groups[e]]:
                a, b = groups[e], i
                break
            groups[e] = i
        else:
            self.fail("Expected two distinct reachable candidate IDs at identical integer energy")
        for x, y in [(a, b), (b, a)]:
            res = p.judge_return("O3", d, [witness(d, x), witness(d, y)])
            self.assertEqual(res["rows"][0]["energy"], res["rows"][1]["energy"])
            self.assertEqual(res["primary"]["id"], int(d["ids"][x]))

    def test_partial_extraction_never_combines_vectors(self):
        for f in p.SLICES:
            res = self.outcomes[f]["no_strict"]
            self.assertEqual(res["status"], "VALID_COMPLETED")
            self.assertIsNone(res["primary"])
            self.assertEqual(res["secondary"]["min_strict_regret"], None)
            self.assertEqual([r["invalid_groups"] for r in res["rows"]], [[1], [2]])
            self.assertIsNone(res["forecast"])

    def test_one_malformed_vector_invalidates_whole_return(self):
        d = self.data["NO2"]
        hit, _, _ = select_witnesses(d)
        for broken in [hit[:-1], hit * 0, hit.astype(float) * np.nan]:
            res = p.judge_return("NO2", d, [hit, broken])
            self.assertEqual(res["status"], "INVALID_RETURN")
            self.assertIsNone(res["primary"])

    def test_impossible_residual_is_contract_error(self):
        d = self.data["FO2"].copy()
        win = int(np.argmin(d["values"]))
        d["D"] = d["D"].copy()
        d["D"][win] = 4
        res = p.judge_return("FO2", d, [witness(d, win)])
        self.assertEqual(res["status"], "CONTRACT_ERROR")
        self.assertIsNone(res["primary"])

    def test_wrong_slice_matrix_with_same_spin_count_is_rejected(self):
        wrong = self.data["NO2"]
        spin = witness(wrong, int(np.argmin(wrong["values"])))
        res = p.judge_return("O3", wrong, [spin])
        self.assertEqual(res["status"], "CONTRACT_ERROR")
        self.assertEqual(res["reason"], "MATRIX_FAMILY_MISMATCH")

    def test_one_sided_boundaries(self):
        for f, (lo, hi, _, _) in p.REFERENCES.items():
            self.assertEqual([p.forecast(f, n) for n in (lo-4, lo, hi, hi+4, None)],
                             ["BETTER_THAN_SINGLE_SA", "WITHIN_REFERENCE", "WITHIN_REFERENCE",
                              "WORSE_THAN_SINGLE_SA", None])

    def test_mismatch_uses_adjacent_planned_slots_same_matrix(self):
        f = "O3"
        above = self.outcomes[f]["hit"].copy()
        above["primary"] = dict(above["primary"], residual=p.REFERENCES[f][1]+4)
        rec = {slot: dict(self.record(slot), outcome=above) for slot in ("F01", "F06", "F08")}
        rows = p.summarize(rec)["slots"]
        self.assertEqual([rows[i]["prediction_mismatch"] for i in (0, 5, 7)], [False, True, True])
        for mid in [self.record("F06"), self.record("F06", status="PENDING")]:
            rec["F06"] = mid
            self.assertFalse(p.summarize(rec)["slots"][7]["prediction_mismatch"])

    def test_round_denominators_and_secondary_aggregate(self):
        rec = {slot: self.record(slot) for slot in p.SLOTS}
        rec["F02"] = self.record("F02", "miss")
        rec["F09"] = self.record("F09", status="PENDING")
        s = p.summarize(rec)
        self.assertEqual((s["achieved"], s["completed_rounds"], s["planned_rounds"]), (1, 2, 3))
        self.assertFalse(s["rounds"][0]["joint_exact"])
        self.assertTrue(s["rounds"][0]["aggregate_exact"])
        self.assertTrue(s["rounds"][0]["observed_quality_failure"])
        self.assertFalse(s["rounds"][2]["observed_quality_failure"])
        self.assertEqual(s["achieved_per_completed"], .5)
        self.assertIsNone(p.summarize({})["achieved_per_completed"])
        rec["F02"] = self.record("F02", "no_strict")
        r = p.summarize(rec)["rounds"][0]
        self.assertTrue(r["complete"])
        self.assertFalse(r["strict_coverage"])
        self.assertIsNone(r["max_slice_regret"])

    def test_duplicate_ids_and_cache(self):
        rec = {slot: self.record(slot) for slot in p.SLOTS}
        rec["F06"]["task_id"] = rec["F01"]["task_id"]
        rec["F03"]["task_id"] = sorted(p._history_ids())[0]
        s = p.summarize(rec)
        self.assertEqual(s["completed_rounds"], 1)
        self.assertEqual([row["slot"] for row in s["slots"] if row["status"] == "DUPLICATE"],
                         ["F03", "F06"])

    def test_first_gate_ignores_quality_but_waits_for_integrity(self):
        now = p.STOP - timedelta(hours=1)
        rec = {"F01": self.record("F01", status="PENDING")}
        self.assertEqual(p.ledger_gate("F02", rec, now), "WAIT_FIRST_RETURN_INTEGRITY")
        for kind in ["miss", "no_strict"]:
            rec["F01"] = self.record("F01", kind)
            self.assertEqual(p.ledger_gate("F02", rec, now), "READY_OFFLINE")
        rec["F02"] = self.record("F02", status="PENDING")
        self.assertEqual(p.ledger_gate("F03", rec, now), "READY_OFFLINE")
        rec["F02"]["billing"]["attributable"] = False
        self.assertEqual(p.ledger_gate("F03", rec, now), "PAUSE_UNVERIFIED_BILLING")
        rec["F02"]["billing"]["after"]["1000"] = 1
        self.assertEqual(p.ledger_gate("F03", rec, now), "PAUSE_1000_DEBIT")

    def test_no_replacement_or_late_creation(self):
        now = p.STOP - timedelta(seconds=1)
        rec = {"F01": self.record("F01", status="CREATE_FAILED")}
        self.assertEqual(p.ledger_gate("F01", rec, now), "STOP_RETRY_OR_OUT_OF_ORDER")
        self.assertEqual(p.ledger_gate("F10", rec, now), "STOP_NONFORMAL_SLOT")
        self.assertEqual(p.ledger_gate("F01", {}, p.STOP), "STOP_DEADLINE")
        self.assertNotEqual(p.ledger_gate("F03", {"F01": self.record("F01")}, now), "READY_OFFLINE")

    def test_preflight_checks_the_git_anchor(self):
        now = p.STOP - timedelta(seconds=1)
        with patch.object(p.subprocess, "run") as verify:
            self.assertEqual(p.creation_gate("a"*40, "F01", {}, now), "READY_OFFLINE")
            self.assertIn("--anchor", verify.call_args.args[0])
            self.assertTrue(verify.call_args.kwargs["check"])
        with self.assertRaises(ValueError):
            p.creation_gate("a"*7, "F01", {}, now)


if __name__ == "__main__":
    unittest.main()
