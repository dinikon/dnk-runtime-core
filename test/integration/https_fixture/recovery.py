import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from types import SimpleNamespace
from uuid import uuid4
from django.conf import settings
import httpx
import ssl

root = Path(os.environ["DNK_HTTPS_FIXTURE_DIRECTORY"])
settings.configure(
    RUNTIME_CA_FILE=str(root / "ca.crt"),
    RUNTIME_CLIENT_CERT_FILE=str(root / "core.crt"),
    RUNTIME_CLIENT_KEY_FILE=str(root / "core.key"),
)
spec = importlib.util.spec_from_file_location(
    "real_core_runtime",
    str(Path(os.environ["DNK_CORE_REPOSITORY"]) / "src/operations/runtime.py"),
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
client = module.RuntimeClient(
    SimpleNamespace(management_origin="https://runtime-management.example.test")
)
installed = json.loads((root / "installed.json").read_text())
os.kill(json.loads((root / "pids.json").read_text())["worker"], signal.SIGKILL)
print(
    "Stopped task worker abruptly; waiting for its persisted heartbeat to expire.",
    flush=True,
)
time.sleep(32)
assert client.status()["ready"] is False
payload = json.loads(json.dumps(installed[0]["command"]))
payload.update(
    tenant_id=str(uuid4()),
    operation_id=str(uuid4()),
    attempt_id=str(uuid4()),
    hostname="recovery.first.example.test",
    name="Recovery live",
)
payload["oidc"]["issuer"] = (
    "https://core.example.test/oidc/tenants/" + payload["tenant_id"]
)
payload["oidc"][
    "redirect_uri"
] = "https://recovery.first.example.test/api/auth/cloud/callback/"
payload["oidc"]["client_id"] = "live-" + payload["tenant_id"]
attempt = SimpleNamespace(pk=payload["attempt_id"])
assert client.provision(attempt, payload)["state"] == "queued"
assert client.lookup(attempt)["state"] == "queued"
subprocess.run(
    [
        str(Path(os.environ["DNK_RUNTIME_REPOSITORY"]) / ".venv/bin/python"),
        str(Path(__file__).parent / "restart.py"),
    ],
    check=True,
)
deadline = time.monotonic() + 40
while True:
    try:
        state = client.lookup(attempt)
        if state["state"] == "succeeded":
            break
        assert state["state"] != "failed", state
    except module.RuntimeError:
        pass
    if time.monotonic() > deadline:
        raise AssertionError("Recovery timed out")
    time.sleep(1)
for old in installed:
    assert (
        client.lookup(SimpleNamespace(pk=old["command"]["attempt_id"])) == old["state"]
    )
    assert (
        client.provision(
            SimpleNamespace(pk=old["command"]["attempt_id"]), old["command"]
        )
        == old["state"]
    )
context = ssl.create_default_context(cafile=str(root / "ca.crt"))
with httpx.Client(verify=context, trust_env=False) as public:
    assert (
        public.get(
            "https://recovery.first.example.test/.well-known/dnk/tenant-ready"
        ).json()["ready"]
        is True
    )
result = {
    "expired_worker_removes_instance_readiness": True,
    "acceptance_survives_worker_down_and_api_restart": True,
    "persisted_results_and_encrypted_credentials_survive_restart": True,
    "recovered_attempt_id": payload["attempt_id"],
}
(root / "recovery-verification.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
