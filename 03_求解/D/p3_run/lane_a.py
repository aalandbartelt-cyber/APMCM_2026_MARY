"""One writer for nine optimization-service slots; all exports derive from the ledger."""
import argparse
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SEALED = ROOT / "evidence/p3"
sys.path.insert(0, str(SEALED))
import protocol

A = ROOT / "artifacts/p3_run/A"
STATE = A / "state.json"
ANCHOR = "2e1dab8d3312ad01bac1d71c7edd6ac5fddb7d37"
RECEIPT = "ea291e3e0acd4bda99992e6d44b335121e2875a2be77b0da9a6f84673a396157"
TZ = ZoneInfo("Asia/Shanghai")


def now():
    return datetime.now(TZ)


def timestamp():
    return now().isoformat(timespec="microseconds")


def sync_dir(folder):
    fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json(path, value, immutable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        f.write((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode())
        f.flush()
        os.fsync(f.fileno())
    try:
        if immutable:
            os.link(tmp, path)
        else:
            os.replace(tmp, path)
        sync_dir(path.parent)
    finally:
        tmp.unlink(missing_ok=True)


def save(s, event):
    s["revision"] += 1
    s["event"] = event
    s["updated_at"] = timestamp()
    s["summary"] = protocol.summarize(s["records"])
    history = A / "history" / f'{s["revision"]:05}.json'
    write_json(history, s, immutable=True)
    write_json(STATE, s)


def load():
    # If interrupted between two fsyncs, recover the last completed immutable revision.
    history = sorted((A / "history").glob("*.json"))
    if history:
        last = history[-1].read_bytes()
        if not STATE.exists() or STATE.read_bytes() != last:
            write_json(STATE, json.loads(last))
    return json.loads(STATE.read_text()) if STATE.exists() else None


def init(g550, g1000, quote):
    if load() is not None:
        raise SystemExit("Ledger already exists")
    if hashlib.sha256((SEALED / "receipt.json").read_bytes()).hexdigest() != RECEIPT:
        raise RuntimeError("Receipt SHA mismatch")
    gate = protocol.creation_gate(ANCHOR, "F01", {}, now())
    s = dict(anchor=ANCHOR, receipt_sha256=RECEIPT, timezone=str(TZ),
             stop=protocol.STOP.isoformat(), snapshot=protocol.SNAPSHOT.isoformat(),
             opened_at=timestamp(), revision=0, records={}, attempts={},
             first_return_seen_at=None, baseline_balance={"550":g550,"1000":g1000},
             baseline_evidence={"source":"user_console_readback","verbatim":quote,
                                "recorded_at":timestamp(),"read_time_exact":False},
             startup_preflight=gate)
    save(s, "BASELINE_CONSOLE_READBACK")
    print(gate)


def before_balance(s, slot):
    i = protocol.SLOTS.index(slot)
    if i == 0:
        return s["baseline_balance"]
    return s["records"][protocol.SLOTS[i-1]]["billing"]["after"]


def bill(s, slot, g550, g1000, exclusive, quote):
    r = s["records"][slot]
    if not r.get("task_id"):
        raise ValueError("Actual task ID required")
    if "billing" in r and protocol._billing_status(r["billing"]) == "OK":
        raise ValueError("Billing already reconciled")
    prior = before_balance(s, slot)
    after = {"550":g550,"1000":g1000}
    obs = {"before":prior,"after":after,"attributable":exclusive,
           "recorded_at":timestamp(),"source":"user_console_readback","verbatim":quote}
    r.setdefault("balance_observations", []).append(obs.copy())
    r["billing"] = obs.copy()
    result = protocol._billing_status(obs)
    if result == "PAUSE_1000_DEBIT":
        s["stop_reason"] = result
    save(s, f"{slot}_{result}")
    print(result)


def create(s, slot):
    import cloud_adapter
    if s.get("stop_reason") or slot in s["attempts"]:
        raise RuntimeError("Creation paused or slot already attempted")
    gate = protocol.creation_gate(ANCHOR, slot, s["records"], now())
    if gate != "READY_OFFLINE":
        raise RuntimeError(gate)
    before = before_balance(s, slot)
    if before["550"] < 1:
        raise RuntimeError("No SPQC550 credit available")
    s["attempts"][slot] = dict(intent_at=timestamp(), before=before.copy(), gate=gate)
    save(s, f"{slot}_RESERVED")
    response = cloud_adapter.submit(slot, ANCHOR, s["records"], A / slot)
    apply_response(s, slot, response)


def apply_response(s, slot, response):
    # Transport status and the scientific adjudication are stored separately.
    r = s["records"].setdefault(slot, {"family":protocol.FAMILY[slot]})
    phase = response["state"]
    tid = response.get("result_id")
    if tid:
        if r.get("task_id") not in (None, str(tid)):
            s["stop_reason"] = "SERVER_ID_CHANGED"
            phase = "CONTRACT_ERROR"
        else:
            r["task_id"] = str(tid)
    r["last_transport"] = response
    r["observed_at"] = timestamp()
    if phase in ("RAW_ARCHIVED", "RETURN_AVAILABLE"):
        ingest(s, slot, r)
    elif phase == "SUBMISSION_UNCERTAIN":
        r["status"] = "PENDING"
        s["stop_reason"] = "SUBMISSION_UNCERTAIN"
    elif phase in protocol.STATES:
        r["status"] = phase
    else:
        raise ValueError(f"Unhandled transport status {phase!r}")
    if protocol.slot_records(s["records"])[protocol.SLOTS.index(slot)]["status"] == "DUPLICATE":
        r["status"] = "DUPLICATE"
    if r["status"] in {"DUPLICATE","INVALID_RETURN","CONTRACT_ERROR","CREATE_FAILED"}:
        s["stop_reason"] = r["status"]
    save(s, f'{slot}_{r["status"]}')
    print(slot, r["status"], r.get("task_id"), flush=True)


def ingest(s, slot, r):
    import cloud_adapter
    if s["first_return_seen_at"] is None:
        s["first_return_seen_at"] = timestamp()
    try:
        archive = cloud_adapter.ingest(A / slot)
        r["return_archive"] = archive
        with np.load(SEALED / f'{r["family"]}.npz', allow_pickle=False) as batch:
            vectors = np.load(archive["vectors_path"], allow_pickle=False)
            result = protocol.judge_return(r["family"], batch, vectors)
        r["outcome"] = result
        r["status"] = result["status"]
    except Exception as exc:
        r.update(status="INVALID_RETURN", error_type=type(exc).__name__)


def poll(s, slot):
    import cloud_adapter
    if s["records"].get(slot,{}).get("status") not in ("CREATED","PENDING"):
        raise ValueError("Only existing nonterminal jobs may be polled")
    apply_response(s, slot, cloud_adapter.poll(slot, ANCHOR, A / slot))


def exports(s, folder):
    folder.mkdir(parents=True, exist_ok=True)
    q = s["summary"]
    for label, rows in [("slots", q["slots"]), ("rounds",q["rounds"])]:
        out = []
        for row in rows:
            fields = {k:v for k,v in row.items() if k not in ("primary","secondary")}
            if label == "slots":
                fields.update({key:(row["primary"] or {}).get(key) for key in
                               ("return_index","energy","residual","id","vhat","regret","exact")})
                fields.update({key:(row["secondary"] or {}).get(key) for key in
                               ("exists_strict_hit","min_strict_regret")})
                fields["strict_count"] = s["records"].get(row["slot"],{}).get("outcome",{}).get("strict_count")
            if label == "rounds" and not row["complete"]:
                fields.update(strict_coverage=None, joint_exact=None, observed_quality_failure=None)
            out.append({k:("NA" if v is None else v) for k,v in fields.items()})
        with (folder / f"{label}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0]))
            w.writeheader()
            w.writerows(out)
    with (SEALED/"envelopes.csv").open() as f:
        envelope = {family: [] for family in protocol.SLICES}
        for row in csv.DictReader(f):
            if row["batch"] in envelope:
                envelope[row["batch"]].append((int(row["residual"]),float(row["max_regret"])))
    cols = ("slot","family","position","selected","energy","residual","strict","invalid_groups","id",
            "regret","exact","envelope_max_regret","regret_within_envelope","single_sa_p05","single_sa_p95")
    with (folder/"vectors.csv").open("w",newline="") as f:
        w = csv.DictWriter(f,fieldnames=cols)
        w.writeheader()
        for r in q["slots"]:
            if r["status"] != "VALID_COMPLETED":
                continue
            family = r["family"]
            for obs in s["records"][r["slot"]]["outcome"]["rows"]:
                bound = max(v for t,v in envelope[family] if t <= obs["residual"])
                valid = obs["regret"] <= bound if obs["strict"] else None
                if valid is False:
                    raise ValueError("Decoded regret exceeds the sealed envelope")
                w.writerow(dict(slot=r["slot"],family=family,position=obs["return_index"],
                       selected=r["primary"] is not None and obs["return_index"]==r["primary"]["return_index"],
                       energy=obs["energy"],residual=obs["residual"],strict=obs["strict"],
                       invalid_groups=",".join(map(str,obs["invalid_groups"])),id=obs.get("id","NA"),
                       regret=obs.get("regret","NA"),exact=obs.get("exact","NA"),
                       envelope_max_regret=bound if obs["strict"] else "NA",
                       regret_within_envelope="NA" if valid is None else valid,
                       single_sa_p05=protocol.REFERENCES[family][0],single_sa_p95=protocol.REFERENCES[family][1]))
    write_json(folder/"summary.json", {k:v for k,v in q.items() if k not in ("slots","rounds")} |
               {"as_of":s["updated_at"],"state_revision":s["revision"],"anchor":ANCHOR})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["init","create","poll","bill","report","snapshot"])
    p.add_argument("--slot", choices=protocol.SLOTS)
    p.add_argument("--g550",type=int)
    p.add_argument("--g1000",type=int)
    p.add_argument("--exclusive", action="store_true")
    p.add_argument("--quote")
    v = p.parse_args()
    if v.action in ("bill","init") and (not v.quote or None in (v.g550,v.g1000) or min(v.g550,v.g1000)<0):
        p.error("Both nonnegative balances and their verbatim source are required")
    if v.action in ("bill","create","poll") and not v.slot:
        p.error("slot required")
    A.mkdir(parents=True,exist_ok=True)
    with (A/"writer.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if v.action == "init":
            return init(v.g550,v.g1000,v.quote)
        s = load()
        if v.action == "bill":
            bill(s,v.slot,v.g550,v.g1000,v.exclusive,v.quote)
        elif v.action == "create":
            create(s,v.slot)
        elif v.action == "poll":
            poll(s,v.slot)
        elif v.action == "report":
            exports(s,A/"current")
        else:
            if now() < protocol.SNAPSHOT:
                raise SystemExit("Snapshot time has not arrived")
            cutoff = protocol.SNAPSHOT
            records = [json.loads(f.read_text()) for f in sorted((A/"history").glob("*.json"))]
            last = next(rec for rec in reversed(records) if datetime.fromisoformat(rec["updated_at"]) <= cutoff)
            folder = A/"snapshot_20261129T2100"
            if folder.exists():
                manifest = json.loads((folder/"manifest.json").read_text())
                if manifest["source_revision"] != last["revision"] or any(
                    hashlib.sha256((folder/n).read_bytes()).hexdigest() != h
                    for n,h in manifest["files"].items()
                ):
                    raise RuntimeError("Immutable snapshot no longer matches evidence")
                return
            with tempfile.TemporaryDirectory(dir=A) as tmp:
                draft = Path(tmp)/"snapshot"
                exports(last,draft)
                write_json(draft/"manifest.json",dict(cutoff=cutoff.isoformat(), produced=timestamp(),
                           source_revision=last["revision"], files={f.name:hashlib.sha256(f.read_bytes()).hexdigest()
                           for f in sorted(draft.iterdir())}),immutable=True)
                os.rename(draft,folder)
                sync_dir(A)


if __name__ == "__main__":
    main()
