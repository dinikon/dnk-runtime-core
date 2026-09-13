import os

"""Exercise the real Core RuntimeClient over nginx mTLS and real Runtime workers."""
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import ssl
import time
from types import SimpleNamespace
from uuid import uuid4

import httpx
from django.conf import settings

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
runtime = module.RuntimeClient(
    SimpleNamespace(management_origin="https://runtime-management.example.test")
)
result = {}
deadline = time.monotonic() + 45
while True:
    try:
        status = runtime.status()
    except module.RuntimeError:
        if time.monotonic() > deadline:
            raise
        time.sleep(0.5)
        continue
    zones = {d["base_domain"]: d for d in status["domains"]}
    if status["ready"] and all(
        zones[z]["routing_ready"] and zones[z]["tls_ready"]
        for z in ["first.example.test", "second.example.test"]
    ):
        break
    if time.monotonic() > deadline:
        raise AssertionError(("zone-readiness", status))
    time.sleep(1)
assert zones["missing.example.test"]["tls_ready"] is False
result["zone_readiness"] = status


def context(label=None):
    ctx = ssl.create_default_context(cafile=str(root / "ca.crt"))
    if label:
        ctx.load_cert_chain(str(root / (label + ".crt")), str(root / (label + ".key")))
    return ctx


def get(host, path, cert=None, headers=None):
    with httpx.Client(
        verify=context(cert), trust_env=False, follow_redirects=False, timeout=5
    ) as client:
        return client.get("https://" + host + path, headers=headers)


result["missing_certificate"] = get(
    "runtime-management.example.test", "/internal/v1/status/"
).status_code
assert result["missing_certificate"] in {400, 401, 403}
result["wrong_fingerprint"] = get(
    "runtime-management.example.test", "/internal/v1/status/", "foreign"
).status_code
assert result["wrong_fingerprint"] == 403
result["rotation_overlap"] = get(
    "runtime-management.example.test", "/internal/v1/status/", "core-rotated"
).status_code
assert result["rotation_overlap"] == 200
result["public_internal"] = get(
    "unknown.first.example.test", "/internal/v1/status/", "core"
).status_code
assert result["public_internal"] == 404
result["forged_without_certificate"] = get(
    "runtime-management.example.test",
    "/internal/v1/status/",
    headers={
        "ssl-client-verify": "SUCCESS",
        "ssl-client-cert": (root / "core.crt").read_text().replace("\n", "%0A"),
    },
).status_code
assert result["forged_without_certificate"] in {400, 401, 403}
result["unknown_tenant"] = get(
    "unknown.first.example.test", "/.well-known/dnk/tenant-ready"
).status_code
assert result["unknown_tenant"] == 404
try:
    get("unknown.missing.example.test", "/.well-known/dnk/tenant-ready")
except httpx.ConnectError:
    result["missing_zone_tls_rejected"] = True
else:
    raise AssertionError("Missing zone unexpectedly passed TLS verification")

owner = str(uuid4())
installed = []
for index, zone in enumerate(["first.example.test", "second.example.test"]):
    tenant, operation, attempt = map(str, [uuid4(), uuid4(), uuid4()])
    host = f"owner-{index}.{zone}"
    payload = {
        "tenant_id": tenant,
        "operation_id": operation,
        "attempt_id": attempt,
        "hostname": host,
        "name": f"Runtime live {index}",
        "owner": {
            "sub": owner,
            "verified_email": "owner.integration@example.com",
            "profile": {"first_name": "Integration", "last_name": "Owner"},
        },
        "oidc": {
            "issuer": f"https://core.example.test/oidc/tenants/{tenant}",
            "client_id": "live-" + tenant,
            "client_secret": "local-test-" + str(uuid4()),
            "redirect_uri": f"https://{host}/api/auth/cloud/callback/",
        },
    }
    attempt_object = SimpleNamespace(pk=attempt)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        replies = list(
            executor.map(lambda _: runtime.provision(attempt_object, payload), range(4))
        )
    assert all(reply["attempt_id"] == attempt for reply in replies)
    changed = dict(payload, name="Conflicting command")
    try:
        runtime.provision(attempt_object, changed)
    except module.RuntimeContractError:
        pass
    else:
        raise AssertionError("Same attempt accepted a different payload")
    deadline = time.monotonic() + 40
    while True:
        state = runtime.lookup(attempt_object)
        if state["state"] in {"succeeded", "failed"}:
            break
        if time.monotonic() > deadline:
            raise AssertionError(("install-timeout", state))
        time.sleep(0.5)
    assert (
        state["state"] == "succeeded"
        and state["resources_state"] == "present"
        and state["runtime_tenant_id"]
    ), state
    ready = get(host, "/.well-known/dnk/tenant-ready")
    assert ready.status_code == 200 and ready.json() == {
        "tenant_id": tenant,
        "hostname": host,
        "ready": True,
    }
    assert runtime.provision(attempt_object, payload) == state
    another = dict(payload, attempt_id=str(uuid4()))
    try:
        runtime.provision(SimpleNamespace(pk=another["attempt_id"]), another)
    except module.RuntimeContractError:
        pass
    else:
        raise AssertionError("Existing installation allowed another attempt")
    installed.append({"command": payload, "state": state})
    print(
        "PASS real Core RuntimeClient -> persisted acceptance -> RabbitMQ worker -> PostgreSQL Tenant -> public TLS readiness:",
        zone,
        flush=True,
    )

(root / "installed.json").write_text(json.dumps(installed, indent=2))
(root / "installed.json").chmod(0o600)
result["installations"] = [
    {
        "hostname": r["command"]["hostname"],
        "state": r["state"]["state"],
        "resources_state": r["state"]["resources_state"],
    }
    for r in installed
]
result["concurrent_duplicate_commands"] = 8
result["different_payload_and_new_attempt_rejected"] = True
(root / "verification.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
