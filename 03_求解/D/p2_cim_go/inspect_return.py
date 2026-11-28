"""Read-only download and diagnostics of a specific saved SDK query response.

This does not submit, poll, repair, change model inputs, or treat optimization
returns as raw sampling. Every downloaded snapshot is exclusive and retained.
"""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import io
import json
import os
from pathlib import Path
import pickle
from urllib.parse import urlsplit
import zlib
import numpy as np
import requests
from contract import ROOT, verify, load_input, decode


class PrimitiveUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        raise ValueError("Global objects forbidden in server pickle")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--anchor",required=True)
    p.add_argument("--query",required=True)
    p.add_argument("--snapshot",required=True)
    args=p.parse_args()
    verify(args.anchor)
    query=Path(args.query).resolve()
    live=ROOT/"artifacts/p2_cim_go_20261128/live/P01"
    if not query.is_relative_to(live):raise ValueError("Query must be a saved P01 response")
    raw=query.read_bytes();response=json.loads(raw);d=response["data"]
    if response["code"]!="0":raise ValueError("Unsuccessful query")
    url=d["result"];parts=urlsplit(url)
    if parts.scheme!="https" or parts.hostname!="cim-task-manager-prod.oss-cn-beijing.aliyuncs.com":
        raise ValueError("Unexpected result origin")
    if not args.snapshot.isidentifier():raise ValueError("Simple snapshot name required")
    out=live/args.snapshot;out.mkdir(mode=0o700)
    r=requests.get(url,timeout=45);r.raise_for_status()
    (out/"result.pkl").write_bytes(r.content);os.chmod(out/"result.pkl",0o600)
    meta={"at":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
          "source_query":str(query.relative_to(ROOT)),"source_query_sha256":hashlib.sha256(raw).hexdigest(),
          "server_status_code":d.get("code"),"server_status_text":d.get("task_status"),
          "server_time_consume_uninterpreted":d.get("time_consume"),
          "server_estimated_time":d.get("estimated_time"),
          "server_actual_start_timestamp":None,"server_actual_finish_timestamp":None,
          "download_http_status":r.status_code,"download_server_date":r.headers.get("Date"),
          "bytes":len(r.content),"result_sha256":hashlib.sha256(r.content).hexdigest()}
    (out/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n")
    payload=PrimitiveUnpickler(io.BytesIO(r.content)).load()
    if not isinstance(payload,dict) or payload.get("format")!="ndarray-zlib-v1":
        raise ValueError("Unsupported documented-by-observation result payload")
    shape=payload["shape"];dtype=np.dtype(payload["dtype"])
    if not isinstance(shape,(tuple,list)) or len(shape)!=2 or shape[1]!=490 or not 0<shape[0]<=100000 or dtype.kind not in "fiu":
        raise ValueError("Invalid shape or dtype")
    expected=int(np.prod(shape))*dtype.itemsize
    if expected>64*1024*1024:raise ValueError("Unexpectedly large result")
    dec=zlib.decompressobj();buf=dec.decompress(payload["data"],expected+1)
    if len(buf)!=expected or not dec.eof or dec.unconsumed_tail or dec.unused_data:
        raise ValueError("Invalid compressed payload length")
    spins=np.frombuffer(buf,dtype=dtype).reshape(shape)
    np.save(out/"spins.npy",spins,allow_pickle=False)
    K,q,values,blocks=load_input();report=decode(spins,K,q,values,blocks)
    # Independently calculate energy from upper-triangle edges, not s @ K @ s.
    i,j=np.triu_indices(len(K),1)
    energies=(-2*np.sum(spins[:,i]*spins[:,j]*K[i,j],axis=1)).astype(np.int64)
    assert np.array_equal(energies,[x["energy"] for x in report["rows"]])
    pool=np.load(ROOT/"artifacts/p23_v2/pool_11.npz",allow_pickle=False)
    allowed=np.argwhere(pool["allowed"][:,:,0]);identities=[]
    for c in sorted({r["candidate"] for r in report["rows"] if r["candidate"] is not None}):
        a,b=allowed[c]
        assert pool["allowed"][a,b,0] and pool["vhat"][a,b,0]==values[c]
        identities.append({"index":c,"A":str(pool["A"][a]),"B":str(pool["B"][b]),"X":str(pool["X"][0])})
    report.update(server_status_code=d.get("code"),raw100_contract="NOT_MET" if len(spins)!=100 else "UNVERIFIED",
                  main_raw100_metric_eligible=False,independent_energy_crosscheck=True,
                  provider_energies_present=False,returned_unique_vectors=len(np.unique(spins,axis=0)),
                  decoded_identities=identities,energy_min=int(energies.min()),energy_max=int(energies.max()))
    (out/"diagnostic.json").write_text(json.dumps(report,indent=2)+"\n")
    summary={k:v for k,v in report.items() if k not in ["rows","edge_01_counts"]}
    summary["source_snapshot"]=str(out.relative_to(ROOT));summary["metadata"]=meta
    (out/"public_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    shared=Path("/mnt/d/上海大学__/26亚太杯英文赛/codex/P2_CIM_GO_20261128")
    with (shared/(args.snapshot+"_public_summary.json")).open("x") as f:
        json.dump(summary,f,ensure_ascii=False,indent=2);f.write("\n")
    print(json.dumps({k:summary[k] for k in ["returned_rows","strict_count","strict_hits","partial_count","partial_hits","energy_selected_regret","raw100_contract","server_status_code","decoded_identities"]},indent=2))


if __name__=="__main__":main()
