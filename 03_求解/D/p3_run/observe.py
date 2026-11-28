"""Poll only already registered IDs. Write the as-of tables at the sealed cutoff."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import lane_a as lane

def run(action, *args):
    cmd = [sys.executable, "-B", str(Path(lane.__file__)), action, *args]
    return subprocess.run(cmd, check=False, timeout=180).returncode

def main():
    with (lane.A / "observer.lock").open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.environ["OPENBLAS_NUM_THREADS"] = "1"
        while True:
            # Read atomically for observation; only lane_a may update the state.
            s = json.loads(lane.STATE.read_bytes())
            for k,r in s["records"].items():
                if r["status"] in {"CREATED","PENDING"} and r.get("task_id"):
                    run("poll","--slot",k)
            run("report")
            if len(s["records"]) == len(lane.protocol.SLOTS) and all(
                r["status"] == "VALID_COMPLETED" for r in s["records"].values()
            ):
                # All server IDs are terminal. The local cutoff timer owns the later snapshot.
                break
            if lane.now() >= lane.protocol.SNAPSHOT:
                if run("snapshot") == 0:
                    break
            time.sleep(50)

if __name__ == "__main__":
    main()
