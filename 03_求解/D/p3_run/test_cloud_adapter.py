"""Offline SDK interception against scripted responses, all sockets disabled."""
from contextlib import ExitStack
import json
from pathlib import Path
import pickle
import socket
import tempfile
import unittest
from unittest.mock import patch
import zlib

import kaiwu as kw
import numpy as np
import requests
import cloud_adapter as adapter


class HTTPFixture:
    def __init__(self, data):
        self.content = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.status_code = 200
        self.ok = True
        self.headers = {"Date": "fixture"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def json(self):
        return json.loads(self.content)

    def raise_for_status(self):
        pass

    @property
    def text(self):
        return self.content.decode()

    def iter_content(self, chunk_size):
        yield self.content


class AdapterTest(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.tmp = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch.object(socket.socket, "connect", side_effect=AssertionError("Real network forbidden")))
        self.stack.enter_context(patch.object(adapter.protocol, "creation_gate", return_value="READY_OFFLINE"))
        self.stack.enter_context(patch.object(adapter.protocol, "ledger_gate", return_value="READY_OFFLINE"))
        self.stack.enter_context(patch.object(adapter, "_license", lambda kw: None))
        self.stack.enter_context(patch.object(kw.cim.CIMOptimizer, "_get_authorization", lambda self: "DUMMY"))
        self.stack.enter_context(patch.object(kw.cim.CIMOptimizer, "_upload_file_to_oss", lambda *a, **kw: "offline://matrix"))
        self.calls = []
        self.query = {"code": "10320", "msg": "absent", "data": None}
        self.bad_create = False
        def transmit(session, method, url, **kwargs):
            self.calls.append((method, url))
            if url.endswith(adapter.QUERY):
                return HTTPFixture(self.query)
            if url.endswith(adapter.CREATE):
                if self.bad_create:
                    raise requests.Timeout("offline")
                return HTTPFixture({"code": "0", "msg": "fixture", "data": {"result_id": "fixture001"}})
            raise AssertionError("Unexpected request")
        self.stack.enter_context(patch.object(requests.sessions.Session, "request", transmit))
        self.anchor = "a" * 40

    def submit(self):
        return adapter.submit("F01", self.anchor, {}, self.tmp)

    def test_submit_once_poll_and_decode(self):
        r = self.submit()
        self.assertEqual((r["state"], r["result_id"], r["create_count"]), ("CREATED", "fixture001", 1), r)
        with self.assertRaises(FileExistsError):
            self.submit()
        self.query = {"code": "0", "data": {"code": "1000", "result": "https://" + adapter.RESULT_HOST + "/fixture"}}
        p = adapter.poll("F01", self.anchor, self.tmp)
        self.assertEqual(p["state"], "RETURN_AVAILABLE", p)
        self.assertEqual(sum(url.endswith(adapter.CREATE) for _, url in self.calls), 1)
        vectors = np.ones((10, 490), dtype=np.int8)
        vectors[:4, 0] = -1
        raw = pickle.dumps({"format": "ndarray-zlib-v1", "dtype": "int8", "shape": vectors.shape,
                            "data": zlib.compress(vectors.tobytes())})
        with patch.object(requests, "get", return_value=HTTPFixture(raw)) as download:
            result = adapter.ingest(self.tmp)
            self.assertEqual(result["count"], 10)
            self.assertTrue(np.array_equal(np.load(result["vectors_path"]), vectors))
            self.assertEqual(Path(result["raw_path"]).read_bytes(), raw)
            adapter.ingest(self.tmp)
            self.assertEqual(download.call_count, 1)
        self.assertTrue((self.tmp / "create_intent.json").is_file())
        self.assertNotIn("DUMMY", json.dumps(r))
        self.assertNotIn("https://", json.dumps(p))

    def test_timeout_never_recreates(self):
        self.bad_create = True
        self.assertEqual(self.submit()["state"], "SUBMISSION_UNCERTAIN")
        with self.assertRaises(FileExistsError):
            self.submit()
        adapter.poll("F01", self.anchor, self.tmp)
        self.assertEqual(sum(url.endswith(adapter.CREATE) for _, url in self.calls), 1)

    def test_gate_existing_task_and_malformed_packets(self):
        with patch.object(adapter.protocol, "creation_gate", return_value="WAIT_FIRST_RETURN_INTEGRITY"):
            with self.assertRaisesRegex(ValueError, "WAIT_FIRST_RETURN_INTEGRITY"):
                self.submit()
        self.query = {"code": "0", "msg": "existing", "data": {"code": "2002"}}
        self.assertEqual(self.submit()["state"], "DUPLICATE")
        self.assertFalse(any(url.endswith(adapter.CREATE) for _, url in self.calls))
        with self.assertRaises(ValueError):
            adapter.unpack(pickle.dumps(Path))
        with self.assertRaises(FileNotFoundError):
            adapter.poll("F02", self.anchor, self.tmp / "never_started")


if __name__ == "__main__":
    unittest.main()
