"""Issue a snapshot at the deadline or on explicit authorization after all tasks finish."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import join_results
import lane_a as lane
import mirror_outputs
import replay_cloud

def verify_inputs():
    subprocess.run([sys.executable, "-B", str(lane.SEALED/"verify.py"),
                    "--anchor", lane.ANCHOR], check=True, stdout=subprocess.DEVNULL)
    formal = lane.A.parent/"B/formal"
    receipt = formal/"verification.json"
    stored = receipt.read_bytes()
    verification = json.loads(stored)
    if (verification["planned_restarts"] != 900
            or verification["verified_raw_files"] != 900
            or verification["return_status"] != {"SCORED": 900}):
        raise ValueError("Formal SA verification does not cover 900 scored raw returns")
    for name, expected in verification["outputs"].items():
        if join_results.sha(formal/name) != expected:
            raise ValueError(f"Formal SA output changed: {name}")
    scorer = Path(__file__).with_name("sa")/"score.py"
    if join_results.sha(scorer) != verification["scoring_script_sha256"]:
        raise ValueError("Formal SA scorer differs from the verification receipt")
    subprocess.run([sys.executable, "-B", str(scorer)], check=True, stdout=subprocess.DEVNULL)
    if receipt.read_bytes() != stored:
        raise ValueError("Replayed verification differs from the original receipt")
    return hashlib.sha256(stored).hexdigest()

def issue_completed():
    root = lane.A.parent
    out = root/"snapshot_comparison"
    with (lane.A/"writer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = lane.load()
        records = state["records"]
        slots = set(lane.protocol.SLOTS)
        if (set(state["attempts"]) != slots or set(records) != slots
                or any(r["status"] != "VALID_COMPLETED" for r in records.values())):
            raise ValueError("Early close requires terminal returns for all nine planned slots")
        if lane.now() >= lane.protocol.STOP:
            raise ValueError("Both preregistered deadlines must still be in the future for this early close")
        sa_hash = verify_inputs()
        rev = state["revision"]
        replay = replay_cloud.audit(rev)
        raw_audit = root/"verify"/f"cloud_replay_rev{rev:05}.json"
        if (replay != json.loads(raw_audit.read_bytes())
                or replay["state_sha256"] != join_results.sha(lane.STATE)
                or replay["verified_slots"] != len(slots)
                or any(row["billing"] != "OK" for row in replay["slots"])):
            raise ValueError("Cloud replay, task count or billing disagrees with the terminal ledger")
        completed = join_results.build(False)
        sources = json.loads((completed/"sources.json").read_bytes())
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            draft = Path(tmp)/"snapshot"
            lane.exports(state, draft)
            for path in draft.iterdir():
                if path.read_bytes() != (lane.A/"current"/path.name).read_bytes():
                    raise ValueError(f"Derived export disagrees with recorded source: {path.name}")
            shutil.copyfile(completed/"main.csv", draft/"main.csv")
            main_hash = join_results.sha(draft/"main.csv")
            if sources["state_revision"] != rev or sources["hash_main"] != main_hash:
                raise ValueError("Final main table differs from the verified comparison")
            summary = state["summary"]
            verified = {
                "status": "CLOSED", "mode": "USER_AUTHORIZED_EARLY_TERMINAL",
                "preregistered_last_creation_at": lane.protocol.STOP.isoformat(),
                "preregistered_snapshot_deadline": lane.protocol.SNAPSHOT.isoformat(),
                "authorization": "用户明确授权全部计划任务终态后立即签发快照。",
                "reason": "九个正式服务槽和900次正式SA均已终态完成，无在途数据。提前于预登记截止线冻结是更保守的选择，不改变任何判定规则。",
                "adjudication_rules_changed": False, "pending_tasks": 0,
                "git_anchor": lane.ANCHOR, "sealed_receipt_sha256": lane.RECEIPT,
                "state_revision": rev, "state_sha256": replay["state_sha256"],
                "last_cloud_observation": state["updated_at"],
                "verified_slots": replay["verified_slots"], "verified_vectors": replay["verified_vectors"],
                "audit_sha256": join_results.sha(raw_audit), "sa_verified_vectors": 900,
                "sa_verification_sha256": sa_hash, "main_sha256": main_hash,
                "achieved_rounds": summary["achieved"], "planned_rounds": summary["planned_rounds"],
                "completed_rounds": summary["completed_rounds"],
                "files": {p.name:join_results.sha(p) for p in sorted(draft.iterdir())},
            }
            if out.exists():
                old = json.loads((out/"closure.json").read_bytes())
                for field,value in verified.items():
                    if old.get(field) != value:
                        raise ValueError(f"Existing closure differs on {field}")
                if any(join_results.sha(out/n) != h for n,h in verified["files"].items()):
                    raise ValueError("Published snapshot contents differ from the receipt")
            else:
                lane.write_json(draft/"closure.json", dict(verified, issued_at=lane.timestamp()), immutable=True)
                os.rename(draft,out)
                lane.sync_dir(root)
    mirror_outputs.sync()

def main():
    if lane.now() < lane.protocol.SNAPSHOT:
        raise SystemExit("Cutoff has yet to occur")
    scripts = Path(__file__).resolve().parent
    subprocess.run([sys.executable, "-B", str(scripts/"lane_a.py"), "snapshot"], check=True)
    a = lane.A/"snapshot_20261129T2100"
    revision = json.loads((a/"manifest.json").read_text())["source_revision"]
    subprocess.run([sys.executable, "-B", str(scripts/"replay_cloud.py"), "--revision",str(revision)], check=True)
    sa_sha = verify_inputs()
    out = join_results.build(True)
    audit = lane.A.parent/"verify"/f"cloud_replay_rev{revision:05}.json"
    checked = json.loads(audit.read_text())
    closure = {"cutoff":lane.protocol.SNAPSHOT.isoformat(),"state_revision":revision,
               "verified_slots":checked["verified_slots"],"verified_vectors":checked["verified_vectors"],
               "audit_sha256":hashlib.sha256(audit.read_bytes()).hexdigest(),
               "sa_verification_sha256":sa_sha,
               "main_sha256":hashlib.sha256((out/"main.csv").read_bytes()).hexdigest()}
    receipt = out/"closure.json"
    if receipt.exists():
        if json.loads(receipt.read_text()) != closure:
            raise ValueError("Closure receipt disagrees with replay")
    else:
        lane.write_json(receipt,closure,immutable=True)
    mirror_outputs.sync()

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--early-terminal", action="store_true", help="issue the user-authorized completed-run snapshot")
    if parser.parse_args().early_terminal:
        issue_completed()
    else:
        main()
