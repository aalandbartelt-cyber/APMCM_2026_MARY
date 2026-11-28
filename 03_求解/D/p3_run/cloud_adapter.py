"""P3 optimization-service transport, to be called by the sole ledger owner.

submit(slot, anchor, records, slot_dir) consumes at most one create opportunity.
poll(slot, anchor, slot_dir) can query only the recorded slot and never creates.
ingest(slot_dir) downloads the first terminal response and preserves vector order.
All raw replies are private; the returned small dictionaries contain no URLs.
Call in a dedicated Python process (SDK checkpoint and requests hook are global).
"""
import contextlib
import hashlib
import importlib.util
from importlib.metadata import version
import io
import json
import logging
import os
from pathlib import Path
import pickle
import sys
import tempfile
from datetime import datetime
from urllib.parse import urlsplit
from unittest.mock import patch
from zoneinfo import ZoneInfo
import zlib

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[3]
SEALED = ROOT / "evidence/p3"
_spec = importlib.util.spec_from_file_location("p3_sealed_protocol", SEALED / "protocol.py")
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)
CREATE = "/api/system/software_task_manager_pro/create_sdk_task/"
QUERY = "/api/system/software_task_manager_pro/get_sdk_task_result/"
API_HOST = "new-open.qboson.com"
RESULT_HOST = "cim-task-manager-prod.oss-cn-beijing.aliyuncs.com"
MD5 = {"O3": "077ea9f4cd37b22b26d5797074f86b8c", "NO2": "c53bcb268e7cffc0b2912799006da167",
       "FO2": "68da57722ecc4eefa32003770a819798"}
SZ = ZoneInfo("Asia/Shanghai")


def now():
    return datetime.now(SZ)


def write_once(path, data):
    """Publish complete bytes atomically without replacing a previous artifact."""
    fd, tmp = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.link(tmp, path)
        dfd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        os.unlink(tmp)


def save(path, value):
    write_once(path, (json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode())


def read(path):
    return json.loads(path.read_bytes())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _license(kw):
    spec = importlib.util.spec_from_file_location("p3_local_license", ROOT / "configs/kaiwu_license.py")
    credentials = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(credentials)
    kw.license.init(user_id=credentials.KAIWU_USER_ID, sdk_code=credentials.KAIWU_SDK_CODE)


@contextlib.contextmanager
def _quiet_sdk():
    # SDK handlers can hold the original stderr even after redirect_stderr.
    previous = logging.root.manager.disable
    logging.disable(sys.maxsize)
    try:
        yield
    finally:
        logging.disable(previous)


def submit(slot, anchor, records, slot_dir):
    decision = protocol.creation_gate(anchor, slot, records, now())
    if decision != "READY_OFFLINE":
        raise ValueError(decision)
    return _call("submit", slot, anchor, records, Path(slot_dir))


def poll(slot, anchor, slot_dir):
    return _call("poll", slot, anchor, None, Path(slot_dir))


def task_name(slot, anchor):
    return f"AP26_P3_{anchor[:12]}_{slot}_{protocol.FAMILY[slot]}"


def _call(action, slot, anchor, records, out):
    family = protocol.FAMILY[slot]
    sdk_name = task_name(slot, anchor)
    with np.load(SEALED / f"{family}.npz", allow_pickle=False) as sealed:
        matrix = sealed["J"]
    matrix_sha = digest(matrix.astype("<i8", copy=False).tobytes())
    if matrix_sha != protocol.MATRIX_SHA[family]:
        raise ValueError("Sealed matrix hash mismatch")
    identity = {"anchor": anchor, "slot": slot, "family": family, "task_name": sdk_name,
                "matrix_sha256": matrix_sha, "sdk_md5": MD5[family], "mode": "optimization"}
    if action == "submit":
        out.mkdir(mode=0o700, parents=True, exist_ok=True)
        save(out / "slot_intent.json", {**identity, "at": now().isoformat()})
    else:
        intent = read(out / "slot_intent.json")
        if any(intent.get(k) != v for k, v in identity.items()) or not (out / "create_intent.json").exists():
            raise ValueError("Query identity or prior create intent missing")
    invocation = Path(tempfile.mkdtemp(prefix=action + "_", dir=out))
    safe = {**identity, "state": "PENDING", "started_at": now().isoformat(),
            "result_id": None, "create_count": 0, "request_dir": str(invocation), "events": []}
    if (out / "created.json").exists():
        safe["result_id"] = read(out / "created.json")["result_id"]
    session_request = requests.sessions.Session.request

    def guard(session, method, url, **kwargs):
        parts = urlsplit(url)
        kind = parts.path
        if kind not in (CREATE, QUERY):
            kwargs.setdefault("timeout", 45)
            return session_request(session, method, url, **kwargs)
        if parts.scheme != "https" or parts.netloc != API_HOST:
            raise ValueError("Unexpected task endpoint host")
        if kind == CREATE:
            if action != "submit" or safe["create_count"] or method.upper() != "POST":
                raise RuntimeError("Duplicate or query-time creation refused")
            payload = kwargs.get("data")
            expected = {"task_name": sdk_name, "bit_num": len(matrix), "sample_number": 100,
                        "task_mode": "optimization", "sample_sort_mode": 2, "file_hash": MD5[family]}
            if not isinstance(payload, dict) or any(payload.get(k) != v for k, v in expected.items()):
                raise ValueError("SDK create payload differs from frozen input")
            decision = protocol.ledger_gate(slot, records, now())
            if decision != "READY_OFFLINE":
                raise ValueError(decision)
            save(out / "create_intent.json", {**identity, **expected, "at": now().isoformat()})
            safe["create_count"] += 1
        else:
            params = kwargs.get("params") or {}
            names = {sdk_name, sdk_name + "_" + MD5[family]}
            if method.upper() != "GET" or params.get("task_name") not in names or params.get("md5_num") != MD5[family]:
                raise ValueError("Unbound query refused")
        kwargs.update(timeout=45, allow_redirects=False)
        event = {"kind": "create" if kind == CREATE else "query", "started_at": now().isoformat()}
        safe["events"].append(event)
        response = session_request(session, method, url, **kwargs)
        raw = response.content
        path = invocation / f"{len(safe['events']):03d}_{event['kind']}.bin"
        write_once(path, raw)
        event.update(http_status=response.status_code, ended_at=now().isoformat(), sha256=digest(raw),
                     path=str(path), server_date=response.headers.get("Date"))
        body = json.loads(raw)
        code = str(body.get("code"))
        data = body.get("data") or {}
        event["response_code"] = code
        if kind == CREATE:
            rid = data.get("result_id") if isinstance(data, dict) else None
            if response.ok and code == "0" and rid is not None and str(rid).strip():
                safe.update(state="CREATED", result_id=str(rid))
                save(out / "created.json", {**identity, "result_id": str(rid), "at": event["ended_at"],
                                            "source": str(path), "sha256": digest(raw)})
            else:
                safe["state"] = "CREATE_FAILED"
        elif action == "submit" and code != "10320":
            safe["state"] = "DUPLICATE" if code == "0" else "CONTRACT_ERROR"
            raise ValueError("Server preflight did not confirm absent task")
        elif action == "poll":
            remote_code = str(data.get("code")) if isinstance(data, dict) else None
            safe.update(query_path=str(path), remote_status=remote_code)
            if response.ok and code == "0" and remote_code == "1000":
                try:
                    write_once(out / "terminal_query.bin", raw)
                except FileExistsError:
                    pass
                safe["state"] = "RETURN_AVAILABLE"
            elif response.ok and code == "0" and remote_code == "4001":
                safe["state"] = "RUN_FAILED"
        return response

    try:
        with open(os.devnull, "w") as null, _quiet_sdk(), contextlib.redirect_stdout(null), contextlib.redirect_stderr(null):
            import kaiwu as kw
            if version("kaiwu") != "1.4.4":
                raise ValueError("SDK version drift")
            cache = invocation / "cache"
            cache.mkdir(mode=0o700)
            with patch.object(requests.sessions.Session, "request", guard), patch.object(
                    kw.common.CheckpointManager, "save_dir", str(cache)):
                _license(kw)
                opt = kw.cim.CIMOptimizer(task_name=sdk_name, task_mode="optimization",
                                          sample_number=100, wait=False)
                if opt._ising_to_md5_hash(matrix) != MD5[family]:
                    raise ValueError("SDK matrix serialization changed")
                if action == "submit":
                    opt.solve(matrix, negtail_flip=False, sort_solutions=False)
                else:
                    opt.get_task_result(matrix)
    except Exception as e:
        safe["error_type"] = type(e).__name__
    if action == "submit" and safe["state"] == "PENDING":
        safe["state"] = "SUBMISSION_UNCERTAIN" if safe["create_count"] else "CREATE_FAILED"
    safe["finished_at"] = now().isoformat()
    save(invocation / "summary.json", safe)
    return safe


class PrimitivePickle(pickle.Unpickler):
    def find_class(self, module, name):
        raise ValueError("Only primitive pickle data supported")


def unpack(raw):
    if len(raw) > 64 * 1024 * 1024:
        raise ValueError("Return exceeds payload cap")
    stream = io.BytesIO(raw)
    d = PrimitivePickle(stream).load()
    if stream.read(1) or not isinstance(d, dict) or d.get("format") != "ndarray-zlib-v1":
        raise ValueError("Unexpected archive format")
    shape = d["shape"]
    dtype = np.dtype(d["dtype"])
    if (not isinstance(shape, (tuple, list)) or len(shape) != 2 or any(type(v) != int for v in shape)
            or shape[1] != 490 or not 1 <= shape[0] <= 100000 or dtype.kind not in "fiu"):
        raise ValueError("Invalid return shape or dtype")
    length = shape[0] * shape[1] * dtype.itemsize
    if length > 64 * 1024 * 1024 or not isinstance(d["data"], bytes):
        raise ValueError("Unexpected return size")
    dec = zlib.decompressobj()
    buf = dec.decompress(d["data"], length + 1)
    if len(buf) != length or not dec.eof or dec.unused_data or dec.unconsumed_tail:
        raise ValueError("Corrupt compressed return")
    vectors = np.frombuffer(buf, dtype).reshape(shape)
    if not np.isin(vectors, (-1, 1)).all():
        raise ValueError("Return has non-spin values")
    return vectors


def ingest(slot_dir):
    out = Path(slot_dir)
    accepted = read(out / "created.json")
    terminal = read(out / "terminal_query.bin")
    data = terminal["data"]
    if str(terminal.get("code")) != "0" or str(data.get("code")) != "1000":
        raise ValueError("Terminal status missing")
    result_path = out / "result.pkl"
    if not result_path.exists():
        url = data["result"]
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != RESULT_HOST:
            raise ValueError("Unexpected download origin")
        with requests.get(url, timeout=45, allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                raise RuntimeError(f"Download HTTP {response.status_code}")
            content = bytearray()
            for chunk in response.iter_content(65536):
                if len(content) + len(chunk) > 64 * 1024 * 1024:
                    raise ValueError("Return exceeds payload cap")
                content.extend(chunk)
            write_once(result_path, content)
    raw = result_path.read_bytes()
    vectors = unpack(raw)
    buff = io.BytesIO()
    np.save(buff, vectors, allow_pickle=False)
    vector_path = out / "vectors.npy"
    expected = buff.getvalue()
    if not vector_path.exists():
        write_once(vector_path, expected)
    elif digest(vector_path.read_bytes()) != digest(expected):
        raise ValueError("Archived vector order/content differs from raw return")
    return {"state": "ORDERED_RETURN", "result_id": accepted["result_id"], "count": len(vectors),
            "vectors_path": str(vector_path), "raw_path": str(result_path), "sha256": digest(raw),
            "vectors_sha256": digest(expected), "terminal_query_sha256": digest((out / "terminal_query.bin").read_bytes()),
            "server_time_consume_uninterpreted": data.get("time_consume"), "ingested_at": now().isoformat()}
