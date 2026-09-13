"""Export the Runtime v1 Pydantic contract and synthetic examples; no environment secrets."""

import argparse
import json
from pathlib import Path

from src.modules.control_plane.application.contracts import (
    ProvisioningCommand,
    AttemptResponse,
    StatusResponse,
    AccessProjectionPayload,
    AccessProjectionResponse,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "contracts" / "runtime-v1"
MODELS = {
    "provisioning-command": ProvisioningCommand,
    "attempt-response": AttemptResponse,
    "status-response": StatusResponse,
    "access-put-request": AccessProjectionPayload,
    "access-put-response": AccessProjectionResponse,
}
TENANT = "11111111-1111-4111-8111-111111111111"
OPERATION = "22222222-2222-4222-8222-222222222222"
ATTEMPT = "33333333-3333-4333-8333-333333333333"
USER = "44444444-4444-4444-8444-444444444444"
EVENT = "55555555-5555-4555-8555-555555555555"
RUNTIME = "66666666-6666-4666-8666-666666666666"
HOSTNAME = "sample.one.example.test"
EXAMPLES = {
    "provisioning-command": (
        "provisioning-command",
        {
            "tenant_id": TENANT,
            "operation_id": OPERATION,
            "attempt_id": ATTEMPT,
            "hostname": HOSTNAME,
            "name": "Example tenant",
            "owner": {
                "sub": USER,
                "verified_email": "owner@example.com",
                "profile": {
                    "first_name": "Example",
                    "last_name": "Owner",
                    "display_name": "Example Owner",
                },
            },
            "oidc": {
                "issuer": f"https://core.example.test/oidc/tenants/{TENANT}",
                "client_id": "example-client",
                "client_secret": "EXAMPLE_ONLY_NOT_A_REAL_SECRET",
                "redirect_uri": f"https://{HOSTNAME}/api/auth/cloud/callback/",
            },
        },
    ),
    "attempt-queued": (
        "attempt-response",
        {
            "tenant_id": TENANT,
            "operation_id": OPERATION,
            "attempt_id": ATTEMPT,
            "state": "queued",
            "resources_state": "absent",
            "runtime_tenant_id": None,
            "error_code": None,
        },
    ),
    "attempt-succeeded": (
        "attempt-response",
        {
            "tenant_id": TENANT,
            "operation_id": OPERATION,
            "attempt_id": ATTEMPT,
            "state": "succeeded",
            "resources_state": "present",
            "runtime_tenant_id": RUNTIME,
            "error_code": None,
        },
    ),
    "attempt-failed-unknown": (
        "attempt-response",
        {
            "tenant_id": TENANT,
            "operation_id": OPERATION,
            "attempt_id": ATTEMPT,
            "state": "failed",
            "resources_state": "unknown",
            "runtime_tenant_id": None,
            "error_code": "installation_failed",
        },
    ),
    "status-two-zones": (
        "status-response",
        {
            "ready": True,
            "protocol_version": 1,
            "domains": [
                {
                    "base_domain": "one.example.test",
                    "routing_ready": True,
                    "tls_ready": True,
                },
                {
                    "base_domain": "two.example.test",
                    "routing_ready": True,
                    "tls_ready": False,
                },
            ],
        },
    ),
    "access-put-request": (
        "access-put-request",
        {"event_id": EVENT, "version": 1, "available": True},
    ),
    "access-put-applied": (
        "access-put-response",
        {"status": 200, "data": {"applied": True, "version": 1}},
    ),
    "access-put-duplicate": (
        "access-put-response",
        {"status": 200, "data": {"applied": False}},
    ),
    "access-put-stale": (
        "access-put-response",
        {"status": 200, "data": {"applied": False, "version": 3}},
    ),
}


def documents():
    result = {}
    for name, model in MODELS.items():
        schema = model.model_json_schema(
            mode=(
                "serialization"
                if name in {"attempt-response", "status-response"}
                else "validation"
            )
        )
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"urn:dnk:runtime:v1:{name}"
        result[OUTPUT / f"{name}.schema.json"] = schema
    for name, (model_name, value) in EXAMPLES.items():
        MODELS[model_name].model_validate(value)
        result[OUTPUT / "examples" / f"{name}.json"] = value
    return result


def main(check=False):
    changed = []
    for path, value in documents().items():
        rendered = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        if not path.exists() or path.read_text() != rendered:
            changed.append(path.relative_to(ROOT).as_posix())
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(rendered)
    if check and changed:
        print("Runtime contract artifacts are stale: " + ", ".join(changed))
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    raise SystemExit(main(parser.parse_args().check))
