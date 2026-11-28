"""Meaningful contract tests: never network, never fit or run SA."""
import contextlib
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import contract as c


class DecodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.K, cls.q, cls.v, cls.blocks = c.load_input()
        cls.s = -np.ones(len(cls.K), dtype=np.int64)
        cls.s[-1] = 1
        for b in cls.blocks:
            t = min(range(len(b["mapping"])), key=lambda t: (cls.q[b["mapping"][t]], b["mapping"][t]))
            cls.s[b["start"]:b["start"]+t] = 1

    def run_decode(self, a):
        return c.decode(a, self.K, self.q, self.v, self.blocks)

    def test_ground_and_gauge(self):
        r = self.run_decode(np.array([self.s, -self.s]))
        self.assertEqual(r["strict_hits"], 2)
        self.assertEqual(r["rows"][0]["energy"], r["rows"][1]["energy"])
        self.assertEqual(r["rows"][0]["candidate"], r["rows"][1]["candidate"])

    def test_broken_chain_not_repaired(self):
        x = self.s.copy(); b = self.blocks[0]
        x[b["start"]:b["start"]+2] = [-1, 1]
        r = self.run_decode(x[None, :])
        self.assertEqual(r["strict_count"], 0)
        self.assertEqual(r["partial_count"], 1)
        self.assertGreater(r["rows"][0]["chain_violations"][0], 0)

    def test_no_feasible_keeps_no_regret(self):
        x = self.s.copy()
        for b in self.blocks: x[b["start"]:b["start"]+2] = [-1, 1]
        r = self.run_decode(x[None, :])
        self.assertEqual(r["partial_count"], 0)
        self.assertIsNone(r["best_strict_regret"])
        self.assertIsNone(r["rows"][0]["regret"])

    def test_raw100_not_inferred_from_row_count(self):
        r = self.run_decode(np.repeat(self.s[None, :], 100, axis=0))
        self.assertEqual(r["strict_hits"], 100)  # duplicates retain multiplicity
        self.assertFalse(c.check_raw100_contract(r, False))
        self.assertTrue(c.check_raw100_contract(r, True))
        r3 = self.run_decode(np.repeat(self.s[None, :], 3, axis=0))
        self.assertFalse(c.check_raw100_contract(r3, True))

    def test_bad_spins_and_energy(self):
        for bad in [self.s, np.zeros((1,490)), np.full((1,490),np.nan), np.ones((1,489))]:
            with self.assertRaises(ValueError): self.run_decode(bad)
        r = self.run_decode(self.s[None, :]); energy=r["rows"][0]["energy"]
        c.check_provider_energy(r, [energy], "-sTKs")
        with self.assertRaises(ValueError): c.check_provider_energy(r, [energy+1], "-sTKs")
        with self.assertRaises(ValueError): c.check_provider_energy(r, [energy], "unknown")


class GateTests(unittest.TestCase):
    def test_budget(self):
        for b, expected in [(36,25),(20,15),(4,None),(10,None)]:
            r=c.budget_decision({"550":b,"1000":2},{"550":b-1,"1000":2},True)
            self.assertEqual(r.get("operational_slots"),expected)
        self.assertTrue(c.budget_decision({"a":36},{"a":36},True)["status"].startswith("PAUSE"))
        self.assertTrue(c.budget_decision({"a":36},{"a":35},False)["status"].startswith("PAUSE"))
        self.assertTrue(c.budget_decision({"a":36,"b":2},{"a":35,"b":1},True)["status"].startswith("PAUSE"))

    def test_deadline(self):
        tz=ZoneInfo("Asia/Shanghai")
        self.assertTrue(c.can_start(datetime(2026,11,29,17,59,59,tzinfo=tz)))
        self.assertFalse(c.can_start(datetime(2026,11,29,18,tzinfo=tz)))

    def test_nesting_and_failed_denominators(self):
        statuses=["VALID_COMPLETED","VALID_COMPLETED","PENDING","SUBMISSION_FAILED","NOT_STARTED"]
        r=c.nested_counts(statuses,[True,False,False,False,False],[True,False,False,False,False])
        self.assertEqual(r,dict(N=5,N_A=4,N_V=2,N_F=1,N_eps=1))
        with self.assertRaises(ValueError): c.nested_counts(["PENDING"],[True],[True])

    def test_anchor_tamper_and_later_receipt_rejected(self):
        first="a"*40; later="b"*40
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/"codex/p2_cim_go").mkdir(parents=True)
            f=root/"fixed.txt";f.write_text("fixed")
            receipt={"files":{"fixed.txt":c.sha(f)},"certificate":{"G1":"CERTIFIED","G2":"CERTIFIED"}}
            raw=json.dumps(receipt).encode();(root/c.RECEIPT).write_bytes(raw)
            def git(args,**kwargs):
                return (first+"\n"+later+"\n").encode() if args[1]=="rev-list" else raw
            with patch.object(c,"ROOT",root),patch.object(c.subprocess,"check_output",git):
                c.verify(first)
                with self.assertRaises(ValueError): c.verify(later)
                f.write_text("tampered")
                with self.assertRaises(ValueError): c.verify(first)
                f.write_text("fixed");(root/c.RECEIPT).write_text("{}")
                with self.assertRaises(ValueError): c.verify(first)


class SDKEntryTests(unittest.TestCase):
    def test_one_create_and_poll_read_only(self):
        import requests
        import kaiwu as kw
        import pilot_entry as e
        K, q, v, blocks = c.load_input()
        calls=[]
        class Response:
            status_code=200
            def __init__(self,data):self.content=json.dumps(data).encode();self._data=data
            def json(self):return self._data
            def raise_for_status(self):pass
            @property
            def text(self):return self.content.decode()
        def fake_request(self,method,url,**kwargs):
            calls.append((method.lower(),url))
            if url.endswith(e.QUERY):return Response({"code":"10320","data":None,"msg":"offline absent"})
            if url.endswith(e.CREATE):return Response({"code":"0","data":{"task_id":"OFFLINE"},"msg":"offline accepted"})
            raise AssertionError("Unexpected network in test")
        receipt={"task_name_P01":"OFFLINE_P01_INTEGRATION","sdk_matrix_md5":"c53bcb268e7cffc0b2912799006da167"}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/"configs").mkdir();(root/"codex/p2_cim_go").mkdir(parents=True)
            (root/"configs/kaiwu_license.py").write_text("KAIWU_USER_ID='DUMMY'\nKAIWU_SDK_CODE='DUMMY'\n")
            (root/"codex/p2_cim_go/quota_before_P01.json").write_text(json.dumps({"optimization_quotas":{"550":36,"1000":2}}))
            with contextlib.ExitStack() as st:
                st.enter_context(patch.object(e,"ROOT",root));st.enter_context(patch.object(e,"OUT",root/"live/P01"))
                st.enter_context(patch.object(e,"verify",lambda _:receipt))
                st.enter_context(patch.object(e,"load_input",lambda:(K,q,v,blocks)))
                st.enter_context(patch.object(requests.sessions.Session,"request",fake_request))
                st.enter_context(patch.object(socket.socket,"connect",side_effect=AssertionError("network forbidden")))
                st.enter_context(patch.object(kw.license,"init",lambda **_:None))
                st.enter_context(patch.object(kw.cim.CIMOptimizer,"_get_authorization",lambda _:"DUMMY"))
                st.enter_context(patch.object(kw.cim.CIMOptimizer,"_upload_file_to_oss",lambda *a,**k:"offline://matrix"))
                with patch.object(sys,"argv",["pilot_entry.py","submit","--anchor","a"*40]),contextlib.redirect_stdout(io.StringIO()):
                    e.main()
                    with self.assertRaises(FileExistsError):e.main()
                self.assertEqual(sum(m=="post" for m,u in calls),1)
                with patch.object(sys,"argv",["pilot_entry.py","poll","--anchor","a"*40]),contextlib.redirect_stdout(io.StringIO()):e.main()
                self.assertEqual(sum(m=="post" for m,u in calls),1)
                self.assertTrue((root/"live/P01/create_intent.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
