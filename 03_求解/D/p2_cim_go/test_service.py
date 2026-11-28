import contextlib
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import service_contract as c
from contract import load_input, decode


class ServiceTests(unittest.TestCase):
    def test_task_units_no_solution_rates(self):
        path=Path('artifacts/p2_cim_go_20261128/live/P01/completed_01/diagnostic.json')
        row=c.service_row('F01',json.loads(path.read_text()),'fixture','hash')
        self.assertEqual(row['returned_set_size'],10)
        self.assertTrue(row['hit_strict']);self.assertEqual(row['best_regret_strict'],0)
        self.assertFalse(any('rate' in k or 'fraction' in k for k in row))
        records=[row]+[{'slot':f'F{i:02}','status':'NOT_STARTED'} for i in range(2,21)]
        result=c.summarize(records)
        self.assertEqual(result['G20']['0'],.05)
        self.assertEqual(result['N_V'],1);self.assertEqual(result['N'],20)

    def test_no_feasible_retained(self):
        k,q,v,blocks=load_input();s=-np.ones(len(k),dtype=int);s[-1]=1
        for b in blocks:s[b['start']:b['start']+2]=[-1,1]
        r=c.service_row('F01',decode(s[None,:],k,q,v,blocks),'id','hash')
        self.assertFalse(r['feasible_strict']);self.assertIsNone(r['best_regret_strict'])
        records=[r]+[{'status':'PENDING'} for _ in range(19)]
        out=c.summarize(records);self.assertEqual(out['N_A'],20);self.assertEqual(out['N_V'],1)
        self.assertEqual(out['G20']['10'],0)

    def test_formal_requires_all_pilots_and_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);audit=root/'audit';live=root/'live';audit.mkdir();live.mkdir()
            receipt={'tasks':{'P01':'x','P02':'y','F01':'z'}}
            with patch.object(c,'AUDIT',audit),patch.object(c,'LIVE',live):
                c.gate_slot('P02',receipt)
                with self.assertRaises(ValueError):c.gate_slot('F01',receipt)
                for i in range(1,6):
                    p=audit/f'P{i:02}';p.mkdir();(p/'result.json').write_text(json.dumps({'status':'VALID_COMPLETED'}))
                c.gate_slot('F01',receipt)
                for i in range(25):
                    p=live/str(i);p.mkdir();(p/'create_intent.json').write_text('{}')
                with self.assertRaises(ValueError):c.gate_slot('P02',receipt)
                with self.assertRaises(ValueError):c.gate_slot('P01',receipt)

    def test_actual_sdk_entry_once_and_readonly_poll(self):
        import requests,kaiwu as kw,service_entry as e
        k,q,v,blocks=load_input();calls=[]
        class Response:
            status_code=200
            def __init__(self,data):self.content=json.dumps(data).encode();self.data=data
            def json(self):return self.data
            def raise_for_status(self):pass
            @property
            def text(self):return self.content.decode()
        def request(self,method,url,**kwargs):
            calls.append((method.lower(),url))
            if url.endswith(e.QUERY):return Response({'code':'10320','data':None,'msg':'offline'})
            if url.endswith(e.CREATE):return Response({'code':'0','data':{'result_id':'OFFLINE'},'msg':'offline'})
            raise AssertionError('Unexpected network')
        receipt={'tasks':{'P02':'OFFLINE_SERVICE_P02'},'sdk_matrix_md5':'c53bcb268e7cffc0b2912799006da167'}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'configs').mkdir();(root/'codex/p2_cim_service').mkdir(parents=True)
            (root/'configs/kaiwu_license.py').write_text("KAIWU_USER_ID='DUMMY'\nKAIWU_SDK_CODE='DUMMY'\n")
            (root/'codex/p2_cim_service/quota_decision.json').write_text(json.dumps({'current_confirmed_quotas':{'550':35,'1000':2}}))
            with contextlib.ExitStack() as st:
                st.enter_context(patch.object(e,'ROOT',root));st.enter_context(patch.object(e,'verify_service',lambda _:receipt))
                st.enter_context(patch.object(e,'gate_slot',lambda *args:None))
                st.enter_context(patch.object(e,'load_input',lambda:(k,q,v,blocks)))
                st.enter_context(patch.object(requests.sessions.Session,'request',request))
                st.enter_context(patch.object(socket.socket,'connect',side_effect=AssertionError('Network forbidden')))
                st.enter_context(patch.object(kw.license,'init',lambda **_:None))
                st.enter_context(patch.object(kw.cim.CIMOptimizer,'_get_authorization',lambda _:'DUMMY'))
                st.enter_context(patch.object(kw.cim.CIMOptimizer,'_upload_file_to_oss',lambda *a,**k:'offline://matrix'))
                with patch.object(sys,'argv',['service_entry.py','submit','--anchor','a'*40,'--slot','P02']),contextlib.redirect_stdout(io.StringIO()):
                    e.main()
                    with self.assertRaises(FileExistsError):e.main()
                with patch.object(sys,'argv',['service_entry.py','poll','--anchor','a'*40,'--slot','P02']),contextlib.redirect_stdout(io.StringIO()):e.main()
        self.assertEqual(sum(m=='post' for m,u in calls),1)


if __name__=='__main__':unittest.main(verbosity=2)
