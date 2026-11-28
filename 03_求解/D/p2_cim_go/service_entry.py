"""At-most-once approved service extension; polling cannot create a task.

Both the original input anchor and first service-extension anchor are enforced.
Five valid pilot service returns are required before a formal task. Raw responses are private.
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from contract import ROOT, INPUT, can_start, load_input
from service_contract import verify_service, gate_slot

OUT = ROOT / "artifacts/p2_cim_go_20261128/live/P01"
CREATE = "/api/system/software_task_manager_pro/create_sdk_task/"
QUERY = "/api/system/software_task_manager_pro/get_sdk_task_result/"


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()


def exclusive_json(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, default=str)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def append_event(data):
    with (OUT / "events.jsonl").open("a") as f:
        f.write(json.dumps({"at": now(), **data}, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["check", "submit", "poll"])
    p.add_argument("--anchor", required=True)
    p.add_argument("--slot", required=True)
    args = p.parse_args()
    global OUT
    receipt = verify_service(args.anchor)
    if args.slot not in receipt["tasks"] or args.slot == "P01":
        raise ValueError("Unknown or previously completed slot")
    OUT = ROOT / "artifacts/p2_cim_go_20261128/live" / args.slot
    task_name = receipt["tasks"][args.slot]
    if args.action == "check":
        print(json.dumps({"anchor_verified": True, "slot": args.slot,
                          "mode": "optimization", "real_submission": False}))
        return
    if args.action == "submit":
        gate_slot(args.slot, receipt)
        if not can_start(datetime.now(ZoneInfo("Asia/Shanghai"))):
            raise RuntimeError("T_stop reached; new submissions forbidden")
        quota = json.loads((ROOT / "codex/p2_cim_service/quota_decision.json").read_text())
        if min(quota["current_confirmed_quotas"].values()) <= 0:
            raise RuntimeError("No positive documented quota for default routing")
        OUT.mkdir(parents=True, exist_ok=True, mode=0o700)
        exclusive_json(OUT / "slot_intent.json", {
            "slot": args.slot, "at": now(), "anchor": args.anchor,
            "task_name": task_name, "mode": "optimization",
            "sample_number_requested": 100, "contract": "OPTIMIZATION_RETURN_SET",
            "quota_before": quota, "not_replaceable": True})
    elif not (OUT / "slot_intent.json").exists():
        raise RuntimeError("Cannot poll an unstarted slot")
    if args.action == "poll" and not (OUT / "create_intent.json").exists():
        raise RuntimeError("No create attempted; cannot invent a pending task")

    # Nothing network-capable is imported before validation and durable intent.
    import requests
    import numpy as np
    import kaiwu as kw
    session_request = requests.sessions.Session.request
    run_id = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%dT%H%M%S%f")
    private = OUT / (args.action + "_" + run_id)
    private.mkdir(mode=0o700)
    count = 0
    creates = 0

    def guarded_request(self, method, url, **kwargs):
        nonlocal count, creates
        count += 1
        parts = urlsplit(url)
        is_create = parts.path == CREATE
        if is_create:
            if args.action != "submit" or creates:
                raise RuntimeError("Duplicate or poll-time creation blocked")
            payload = kwargs.get("data")
            expected = {"task_mode": "optimization", "sample_number": 100,
                        "bit_num": 490, "task_name": task_name,
                        "file_hash": receipt["sdk_matrix_md5"], "sample_sort_mode": 2}
            if not isinstance(payload, dict) or any(payload.get(k) != v for k, v in expected.items()):
                raise RuntimeError("Create request does not match frozen contract")
            if not can_start(datetime.now(ZoneInfo("Asia/Shanghai"))):
                raise RuntimeError("T_stop reached before actual create")
            # A timeout or auth retry may never cause a second POST.
            exclusive_json(OUT / "create_intent.json", {"at": now(), **expected,
                           "anchor": args.anchor, "attempt_number": 1})
            creates += 1
        elif parts.path == QUERY:
            params = kwargs.get("params") or {}
            names = {task_name,
                     task_name + "_" + receipt["sdk_matrix_md5"]}
            if params.get("task_name") not in names or params.get("md5_num") != receipt["sdk_matrix_md5"]:
                raise RuntimeError("Query not bound to anchored task")
        kwargs.setdefault("timeout", 45)
        event = {"request_number": count, "action": args.action,
                 "method": method.upper(), "host": parts.hostname, "path": parts.path,
                 "started_at": now()}
        # Never persist authorization headers, license requests, or credential values.
        try:
            response = session_request(self, method, url, **kwargs)
            event.update(http_status=response.status_code, completed_at=now())
            if is_create or parts.path == QUERY:
                raw_path = private / f"{count:03d}_response.bin"
                raw_path.write_bytes(response.content)
                os.chmod(raw_path, 0o600)
                event["response_sha256"] = hashlib.sha256(response.content).hexdigest()
                try:
                    data = response.json()
                    event["response_code"] = data.get("code") if isinstance(data, dict) else None
                    event["top_level_keys"] = sorted(data) if isinstance(data, dict) else []
                except ValueError:
                    event["parse"] = "NON_JSON"
            append_event(event)
            return response
        except Exception as e:
            event.update(error_type=type(e).__name__, ended_at=now())
            append_event(event)
            raise

    requests.sessions.Session.request = guarded_request
    kw.common.CheckpointManager.save_dir = str(OUT / "cache")
    (OUT / "cache").mkdir(exist_ok=True, mode=0o700)
    safe = {"slot": args.slot, "action": args.action, "anchor": args.anchor,
            "task_name": task_name, "mode": "optimization",
            "sample_number_requested": 100, "contract": "OPTIMIZATION_RETURN_SET",
            "started_at": now()}
    log_path = private / "sdk.log"
    with log_path.open("w") as log, redirect_stdout(log), redirect_stderr(log):
        os.chmod(log_path, 0o600)
        try:
            spec = importlib.util.spec_from_file_location("local_license_private", ROOT / "configs/kaiwu_license.py")
            cfg = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cfg)
            kw.license.init(user_id=cfg.KAIWU_USER_ID, sdk_code=cfg.KAIWU_SDK_CODE)
            K, _, _, _ = load_input()
            opt = kw.cim.CIMOptimizer(task_name=task_name,
                    task_mode="optimization", sample_number=100, wait=False)
            if args.action == "submit":
                result = opt.solve(K, negtail_flip=False, sort_solutions=False)
            else:
                result = opt.get_task_result(K)
            safe["returned_type"] = type(result).__name__
            if isinstance(result, np.ndarray):
                np.save(private / "sdk_return.npy", result, allow_pickle=False)
                safe["returned_shape"] = list(result.shape)
            elif result is not None:
                exclusive_json(private / "sdk_return.json", result)
            safe["status"] = "RETURNED_FOR_INTEGRITY_REVIEW" if result is not None else "PENDING"
        except Exception as e:
            # Do not print raw exception text: it may contain a signed URL.
            safe["status"] = "PENDING" if (OUT / "create_intent.json").exists() else "PRE_CREATE_ERROR"
            safe["exception_type"] = type(e).__name__
            (private / "exception.txt").write_text(str(e))
            os.chmod(private / "exception.txt", 0o600)
    safe.update(create_calls_this_invocation=creates, finished_at=now())
    if args.action == "submit" and creates == 0 and safe.get("returned_type") not in [None, "NoneType"]:
        safe["status"] = "CACHE_OR_EXISTING_TASK_REVIEW_REQUIRED"
    exclusive_json(private / "safe_summary.json", safe)
    append_event(safe)
    print(json.dumps(safe, indent=2))


if __name__ == "__main__":
    main()
