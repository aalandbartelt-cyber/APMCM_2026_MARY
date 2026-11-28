"""Read-only service return ingestion and task-level reporting, with no rates per solution."""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import io
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import zlib
import numpy as np
import requests
from contract import ROOT, load_input, decode
from inspect_return import PrimitiveUnpickler
from service_contract import AUDIT, LIVE, verify_service, service_row, summarize


def sha(data):return hashlib.sha256(data).hexdigest()


def get_id(slot):
    for p in sorted((LIVE/slot).glob("submit_*/*response.bin")):
        try:j=json.loads(p.read_bytes())
        except ValueError:continue
        if j.get("code")=="0" and isinstance(j.get("data"),dict) and j["data"].get("result_id"):
            return j["data"]["result_id"]
    return None


def ingest(slot):
    out=AUDIT/slot;out.mkdir(exist_ok=True)
    if (out/"result.json").exists():return json.loads((out/"result.json").read_text())
    qs=sorted((LIVE/slot).glob("poll_*/sdk_return.json"))
    if not qs:return {"slot":slot,"status":"PENDING"}
    data=json.loads(qs[-1].read_text())
    d=data.get("data") or {};code=d.get("code")
    if code=="4001":
        result={"slot":slot,"status":"COMPUTATION_FAILED","source_query_sha256":sha(qs[-1].read_bytes())}
        with (out/"result.json").open("x") as f:json.dump(result,f,indent=2)
        return result
    if data.get("code")!="0" or code!="1000":return {"slot":slot,"status":"PENDING","remote_status_code":code}
    rid=get_id(slot)
    if not rid:raise ValueError("Missing creation result_id")
    other_ids=[get_id(p.name) for p in LIVE.iterdir() if p.is_dir() and p.name!=slot]
    if rid in other_ids:raise ValueError("Server ID reused across slots")
    # Persist the first observed terminal source before download; later replay
    # uses the saved bytes, never a later, better-looking version.
    if not (out/"terminal_query.json").exists():
        with (out/"terminal_query.json").open("xb") as f:f.write(qs[-1].read_bytes())
        os.chmod(out/"terminal_query.json",0o600)
    terminal=json.loads((out/"terminal_query.json").read_text())["data"]
    if not (out/"result.pkl").exists():
        url=terminal["result"];u=urlsplit(url)
        if u.scheme!="https" or u.hostname!="cim-task-manager-prod.oss-cn-beijing.aliyuncs.com":
            raise ValueError("Unexpected result origin")
        r=requests.get(url,timeout=45);r.raise_for_status()
        with (out/"result.pkl").open("xb") as f:f.write(r.content)
        os.chmod(out/"result.pkl",0o600)
    raw=(out/"result.pkl").read_bytes()
    pack=PrimitiveUnpickler(io.BytesIO(raw)).load()
    assert isinstance(pack,dict) and pack["format"]=="ndarray-zlib-v1"
    shape=tuple(pack["shape"]);dtype=np.dtype(pack["dtype"])
    assert len(shape)==2 and shape[1]==490 and 0<shape[0]<=100000 and dtype.kind in "fiu"
    length=int(np.prod(shape))*dtype.itemsize;assert length<=64*1024*1024
    z=zlib.decompressobj();buf=z.decompress(pack["data"],length+1)
    assert len(buf)==length and z.eof and not z.unconsumed_tail and not z.unused_data
    spins=np.frombuffer(buf,dtype=dtype).reshape(shape)
    K,q,v,blocks=load_input();diag=decode(spins,K,q,v,blocks)
    i,j=np.triu_indices(len(K),1)
    for s,row in zip(spins,diag["rows"]):
        assert row["energy"]==int(-2*np.sum(s[i]*s[j]*K[i,j]))
    result=service_row(slot,diag,rid,sha(raw))
    result.update(returned_set_unique_vectors=len(np.unique(spins,axis=0)),
                  min_integer_energy=min(x["energy"] for x in diag["rows"]),
                  max_integer_energy=max(x["energy"] for x in diag["rows"]),
                  server_time_consume_uninterpreted=terminal.get("time_consume"),
                  server_actual_start_timestamp=None,server_actual_finish_timestamp=None,
                  provider_energy_crosscheck="NOT_AVAILABLE",local_energy_crosscheck=True,
                  checked_at=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                  chain_legal_counts=diag["chain_legal_counts"],
                  edge_01_counts=diag["edge_01_counts"])
    np.save(out/"spins.npy",spins,allow_pickle=False)
    (out/"diagnostic.json").write_text(json.dumps(diag,indent=2)+"\n")
    with (out/"result.json").open("x") as f:json.dump(result,f,indent=2);f.write("\n")
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=["ingest","summary"])
    p.add_argument("--anchor",required=True);p.add_argument("--slot")
    args=p.parse_args();verify_service(args.anchor)
    if args.action=="ingest":
        if args.slot not in [f"P{i:02}" for i in range(2,6)]+[f"F{i:02}" for i in range(1,21)]:raise ValueError("Unknown ingest slot")
        r=ingest(args.slot)
        print(json.dumps({k:v for k,v in r.items() if k not in ["chain_legal_counts","edge_01_counts"]},indent=2));return
    records=[]
    for i in range(1,21):
        slot=f"F{i:02}";path=AUDIT/slot/"result.json"
        if path.exists():r=json.loads(path.read_text())
        else:r={"slot":slot,"status":"PENDING" if (LIVE/slot/"create_intent.json").exists() else "NOT_STARTED"}
        records.append(r)
    summary=summarize(records)
    timestamp=datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%dT%H%M%S%f")
    with (AUDIT/("formal_summary_"+timestamp+".json")).open("x") as f:json.dump({"summary":summary,"records":records},f,indent=2);f.write("\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
