"""Approved optimization service contract; no per-returned-solution rates."""
from pathlib import Path
import hashlib
import json
import subprocess
from contract import ROOT, verify as verify_base

BASE_ANCHOR = "87a6c2559249983f43de9d3425e6c820178290aa"
RECEIPT = "codex/p2_cim_service/receipt.json"
LIVE = ROOT / "artifacts/p2_cim_go_20261128/live"
AUDIT = ROOT / "artifacts/p2_cim_go_20261128/service_audit"


def verify_service(anchor):
    verify_base(BASE_ANCHOR)
    history=subprocess.check_output(["git","rev-list","--reverse","HEAD","--",RECEIPT],cwd=ROOT).decode().splitlines()
    if not history or anchor!=history[0]:raise ValueError("Only first service-extension anchor accepted")
    raw=subprocess.check_output(["git","show",anchor+":"+RECEIPT],cwd=ROOT)
    if raw!=(ROOT/RECEIPT).read_bytes():raise ValueError("Service receipt changed")
    r=json.loads(raw)
    for name,h in r["files"].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise ValueError("Changed frozen file: "+name)
    return r


def gate_slot(slot, receipt):
    if slot not in receipt["tasks"] or slot=="P01":raise ValueError("Slot not authorized in extension")
    if slot.startswith("F"):
        for i in range(1,6):
            p=AUDIT/f"P{i:02}"/"result.json"
            if not p.is_file() or json.loads(p.read_text())["status"]!="VALID_COMPLETED":
                raise ValueError("All five pilot service integrity checks must pass")
    intents=list(LIVE.glob("*/create_intent.json"))
    if len(intents)>=25:raise ValueError("25-attempt budget exhausted")
    if (LIVE/slot/"slot_intent.json").exists():raise FileExistsError("Slot already consumed; poll only")


def service_row(slot, diagnostic, result_id, source_hash):
    rows=diagnostic["rows"]
    strict=[r for r in rows if r["strict_feasible"]]
    partial=[r for r in rows if r["partial_usable"]]
    def metrics(rs, suffix):
        e=min(rs,key=lambda r:(r["energy"],r["index"])) if rs else None
        best=min((r["regret"] for r in rs),default=None)
        return {"feasible"+suffix:bool(rs),"hit"+suffix:bool(rs and best==0),
                "near"+suffix:bool(rs and best<=.1),"best_regret"+suffix:best,
                "energy_selected_regret"+suffix:e["regret"] if e else None}
    return {"slot":slot,"stage":"pilot" if slot.startswith("P") else "formal",
            "status":"VALID_COMPLETED","contract":"OPTIMIZATION_RETURN_SET",
            "result_id":result_id,"source_sha256":source_hash,
            "returned_set_size":len(rows),"strict_solution_count":len(strict),
            "partial_solution_count":len(partial),"nominal_ten_deviation":len(rows)!=10,
            **metrics(strict,"_strict"),**metrics(partial,"_partial")}


def summarize(records, n=20):
    if len(records)!=n:raise ValueError("Keep all formal slots in the denominator")
    na=sum(r["status"]!="NOT_STARTED" for r in records)
    valid=[r for r in records if r["status"]=="VALID_COMPLETED"]
    nv=len(valid)
    nf=sum(r["feasible_strict"] for r in valid)
    ne=sum(r["near_strict"] for r in valid)
    nh=sum(r["hit_strict"] for r in valid)
    assert nh<=ne<=nf<=nv<=na<=n
    ratio=lambda a,b:a/b if b else None
    return {"N":n,"N_A":na,"N_V":nv,"N_F":nf,"N_eps":ne,"N_H":nh,
            "attempt_fraction":ratio(na,n),"valid_completion_fraction":ratio(nv,n),
            "near_per_attempt":ratio(ne,na),"near_conditional_valid":ratio(ne,nv),
            "strict_feasible_per_attempt":ratio(nf,na),"near_per_planned_slot":ratio(ne,n),
            "G20":{str(x):sum(r["feasible_strict"] and r["best_regret_strict"]<=x for r in valid)/n for x in [0,.1,.5,1,2,5,10]},
            "G20_partial":{str(x):sum(r["feasible_partial"] and r["best_regret_partial"]<=x for r in valid)/n for x in [0,.1,.5,1,2,5,10]},
            "units":"tasks; no solution-level rates, no TTS"}
