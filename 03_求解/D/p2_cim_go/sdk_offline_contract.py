"""Offline SDK submission contract inspection: every HTTP call is intercepted."""
from pathlib import Path
import json,hashlib,pickle,sys
import numpy as np
import kaiwu as kw
import requests
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/('artifacts/p2_cim_go_20261128/offline_sdk'+('_'+sys.argv[1] if len(sys.argv)>1 else ''))
OUT.mkdir(exist_ok=False);kw.common.CheckpointManager.save_dir=str(OUT/'cache')
trace=[]
class FakeResponse:
    status_code=200
    def __init__(self,data):self.data=data
    def json(self):return self.data
    def raise_for_status(self):pass
    @property
    def text(self):return json.dumps(self.data)
def request(self,method,url,**kwargs):
    trace.append({'method':method,'url':url,'json':kwargs.get('json'),'params':kwargs.get('params'),'data':kwargs.get('data')})
    if url.endswith('get_sdk_task_result/'):return FakeResponse({'code':'10320','data':None,'msg':'not found: offline fixture'})
    if url.endswith('create_sdk_task/'):return FakeResponse({'code':'0','data':{'task_id':'DRY_ONLY'},'msg':'offline fixture'})
    raise RuntimeError('Unexpected offline request: '+url)
requests.sessions.Session.request=request
kw.cim.CIMOptimizer._get_authorization=lambda self:'OFFLINE_DUMMY'
def upload(self,file_name,file_like_object):
    name=file_name;payload=file_like_object
    b=payload.read() if hasattr(payload,'read') else payload
    if isinstance(b,bytes):(OUT/'serialized_payload.pkl').write_bytes(b)
    trace.append({'offline_upload_filename':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    return 'offline://matrix'
kw.cim.CIMOptimizer._upload_file_to_oss=upload
if len(sys.argv)>1 and sys.argv[1].startswith('create'):kw.cim.CIMOptimizer._query_task_status=lambda self,*a:None
K=np.load(ROOT/'artifacts/p2_research_20261128/short_H05/40_real/matrix.npz')['J']
opt=kw.cim.CIMOptimizer(task_name='OFFLINE_CONTRACT_ONLY',wait=False,task_mode='sampling',sample_number=100)
try:
    out=opt.solve(K,negtail_flip=False,sort_solutions=False)
    result={'return_type':type(out).__name__,'return_repr':repr(out)[:300]}
except Exception as e:result={'error':type(e).__name__+': '+str(e)}
result['trace']=trace;result['network_calls']=0
(OUT/'contract.json').write_text(json.dumps(result,indent=2,default=str))
print(json.dumps(result,indent=2,default=str))
