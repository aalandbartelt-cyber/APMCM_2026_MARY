"""Inspect installed SDK modes without credentials, network, or hardware calls.

The HTTP and file-download responses below are synthetic fixtures. They prove
client behavior only, never server billing, returned sample counts or quality.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import importlib.metadata
import inspect
import json
import pickle
import socket
import sys

import kaiwu as kw
import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ("artifacts/p2_cim_go_20261128/" +
              (sys.argv[1] if len(sys.argv) > 1 else "interface_v3_offline"))


def main():
    OUT.mkdir(exist_ok=False)
    trace = []
    current = {}
    network_attempts = []

    def deny_network(*args, **kwargs):
        network_attempts.append("BLOCKED")
        raise RuntimeError("Network forbidden in offline SDK audit")

    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    socket.create_connection = deny_network

    class FakeResponse:
        status_code = 200

        def __init__(self, data=None, content=b""):
            self.data = data
            self.content = content
            self.raw = None

        def json(self):
            return self.data

        def raise_for_status(self):
            pass

        @property
        def text(self):
            return json.dumps(self.data)

        def iter_content(self, chunk_size=8192):
            yield self.content

    def request(self, method, url, **kwargs):
        trace.append({"case": current["name"], "method": method, "url": url,
                      "params": kwargs.get("params"), "data": kwargs.get("data"),
                      "json": kwargs.get("json")})
        if url.endswith("get_sdk_task_result/"):
            return FakeResponse({"code": "10320", "data": None,
                                 "msg": "OFFLINE FIXTURE: absent task"})
        if url.endswith("create_sdk_task/"):
            return FakeResponse({"code": "0", "data": {"task_id": "OFFLINE_ONLY"},
                                 "msg": "OFFLINE FIXTURE: accepted"})
        if url == "https://offline.invalid/result.pkl":
            return FakeResponse(content=pickle.dumps(current["fixture"]))
        raise RuntimeError("Unexpected offline request: " + url)

    requests.sessions.Session.request = request
    kw.cim.CIMOptimizer._get_authorization = lambda self: "OFFLINE_DUMMY"

    def upload(self, file_name, file_like_object):
        payload = (file_like_object.read() if hasattr(file_like_object, "read")
                   else file_like_object)
        trace.append({"case": current["name"], "offline_upload": file_name,
                      "payload_sha256": hashlib.sha256(payload).hexdigest()})
        return "offline://matrix"

    kw.cim.CIMOptimizer._upload_file_to_oss = upload
    source = ROOT / "artifacts/p2_research_20261128/short_H05/40_real/matrix.npz"
    K = np.load(source)["J"]
    results = []
    cases = [("sampling_100", "sampling", 100),
             ("optimization_100", "optimization", 100),
             ("optimization_default", "optimization", None)]
    for name, mode, count in cases:
        current["name"] = name
        (OUT / name).mkdir()
        kw.common.CheckpointManager.save_dir = str(OUT / name / "cache")
        args = dict(task_name="OFFLINE_" + name, wait=False, task_mode=mode)
        if count is not None:
            args["sample_number"] = count
        before = len(trace)
        result = {"case": name, "constructor_args": args}
        try:
            opt = kw.cim.CIMOptimizer(**args)
            returned = opt.solve(K, negtail_flip=False, sort_solutions=False)
            result["return_type"] = type(returned).__name__
            result["local_accepted"] = True
        except Exception as e:
            result["local_accepted"] = False
            result["error"] = type(e).__name__ + ": " + str(e)
        result["trace"] = trace[before:]
        results.append(result)

    # Exercise the common local-cache loader with known local pickle data.
    # Do not invent a server response schema or claim these are real samples.
    fixtures = []
    for mode in ["sampling", "optimization"]:
        for nrows in [3, 100]:
            name = mode + "_synthetic_return_" + str(nrows)
            current["name"] = name
            (OUT / name).mkdir()
            current["fixture"] = np.ones((nrows, 490), dtype=np.int8)
            kw.common.CheckpointManager.save_dir = str(OUT / name / "cache")
            opt = kw.cim.CIMOptimizer(task_name="OFFLINE_" + name,
                                       task_mode=mode, sample_number=100)
            result = {"case": name, "synthetic_rows": nrows, "not_server_evidence": True}
            fixture_path = OUT / (name + ".pkl")
            fixture_path.write_bytes(pickle.dumps(current["fixture"]))
            try:
                out = opt._load_from_file(str(fixture_path))
                result["returned_type"] = type(out).__name__
                result["returned_shape"] = list(np.asarray(out).shape)
                result["equal_fixture"] = bool(np.array_equal(out, current["fixture"]))
            except Exception as e:
                result["error"] = type(e).__name__ + ": " + str(e)
            fixtures.append(result)
    import importlib
    so = Path(importlib.import_module(kw.cim.CIMOptimizer.__module__).__file__)
    report = {
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "scope": "OFFLINE CLIENT AUDIT; no real submission, no real result, no billing evidence",
        "distribution_versions": {n: importlib.metadata.version(n)
                                  for n in ["kaiwu", "kaiwu-community"]},
        "kaiwu_version_attribute": kw.__version__,
        "sdk_binary_sha256": hashlib.sha256(so.read_bytes()).hexdigest(),
        "constructor_signature": str(inspect.signature(kw.cim.CIMOptimizer)),
        "solve_signature": str(inspect.signature(kw.cim.CIMOptimizer.solve)),
        "matrix_file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "matrix_bytes_sha256": hashlib.sha256(K.astype("<i8").tobytes()).hexdigest(),
        "cases": results, "synthetic_return_tests": fixtures,
        "external_network_calls": 0, "blocked_network_attempts": network_attempts,
    }
    (OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    assert not network_attempts
    for case in results:
        assert case["local_accepted"]
        posts = [r for r in case["trace"] if r.get("method") == "post"]
        assert len(posts) == 1
        sent = posts[0]["data"]
        assert sent["task_mode"] == case["constructor_args"]["task_mode"]
        assert sent["sample_number"] == case["constructor_args"].get("sample_number", 10)
        assert sent["bit_num"] == 490 and sent["sample_sort_mode"] == 2
        assert not any(k in sent for k in ["device", "machine", "machine_type"])
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
