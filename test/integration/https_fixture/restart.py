import json
import os
from pathlib import Path
import signal
import subprocess
import time

root = Path(os.environ["DNK_HTTPS_FIXTURE_DIRECTORY"])
repo = Path(os.environ["DNK_RUNTIME_REPOSITORY"])
previous = json.loads((root / "pids.json").read_text())
for pid in previous.values():
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
time.sleep(1)
env = dict(os.environ, **json.loads((root / "environment.json").read_text()))
env["PYTHONPATH"] = str(root) + ":" + str(repo)
pids = {}
for label, args in [
    (
        "api",
        [
            "-m",
            "uvicorn",
            "src.app:app",
            "--host",
            "0.0.0.0",
            "--port",
            os.environ["DNK_HTTPS_API_PORT"],
            "--no-proxy-headers",
        ],
    ),
    ("worker", ["-m", "src.modules.control_plane.worker"]),
]:
    output = (root / (label + ".log")).open("ab")
    process = subprocess.Popen(
        [str(repo / ".venv/bin/python"), *args],
        cwd=repo,
        env=env,
        stdout=output,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    pids[label] = process.pid
(root / "pids.json").write_text(json.dumps(pids))
print("Restarted task-owned Runtime processes", pids)
