"""Published schemas/examples stay tied to the actual v1 models and HTTP router."""

import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from pydantic import ValidationError

from scripts.export_runtime_contracts import EXAMPLES, MODELS, OUTPUT, documents
from src.config.deploy.control_plane import ControlPlaneSettings
from src.modules.control_plane.application.contracts import (
    AccessProjectionResponse,
    AttemptResponse,
    ProvisioningCommand,
    StatusResponse,
)
from src.modules.control_plane.presentation.router import router
from src.modules.shared.presentation.persistence.depends import get_uow


class RuntimeContractArtifactTests(unittest.IsolatedAsyncioTestCase):
    def example(self, name):
        return json.loads((OUTPUT / "examples" / f"{name}.json").read_text())

    def test_generated_schemas_and_synthetic_examples_have_no_drift(self):
        for path, expected in documents().items():
            with self.subTest(path=path.name):
                self.assertEqual(json.loads(path.read_text()), expected)
        for name, (model, _) in EXAMPLES.items():
            MODELS[model].model_validate(self.example(name))

    def test_schema_direction_matches_runtime_and_core_wire_shapes(self):
        attempt = json.loads((OUTPUT / "attempt-response.schema.json").read_text())
        self.assertTrue(
            {
                "tenant_id",
                "operation_id",
                "attempt_id",
                "state",
                "resources_state",
                "runtime_tenant_id",
            }.issubset(attempt["required"])
        )
        status = json.loads((OUTPUT / "status-response.schema.json").read_text())
        self.assertIn("protocol_version", status["required"])
        missing_runtime_id = self.example("attempt-queued")
        del missing_runtime_id["runtime_tenant_id"]
        with self.assertRaises(ValidationError):
            AttemptResponse.model_validate(missing_runtime_id)
        provisioning = json.loads(
            (OUTPUT / "provisioning-command.schema.json").read_text()
        )
        self.assertNotIn("protocol_version", provisioning["properties"])
        self.assertFalse(provisioning["additionalProperties"])
        for malformed in (
            {"status": 200, "data": {"applied": True}},
            {"status": 200, "data": {"applied": False, "version": None}},
            {"status": 200, "data": {"applied": "false"}},
        ):
            with self.assertRaises(ValidationError):
                AccessProjectionResponse.model_validate(malformed)

    async def test_examples_pass_through_actual_runtime_http_router(self):
        application = FastAPI()
        application.state.control_plane_settings = ControlPlaneSettings(
            public_origin="https://core.example.test",
            allowed_base_domains=["one.example.test", "two.example.test"],
        ).model_copy(update={"enabled": True})
        unit_of_work = AsyncMock()
        unit_of_work.session = object()

        async def provide_uow():
            yield unit_of_work

        application.dependency_overrides[get_uow] = provide_uow

        @application.middleware("http")
        async def trust_fixture(request, call_next):
            request.state.control_plane_trusted = True
            return await call_next(request)

        application.include_router(router)
        repository = AsyncMock()
        repository.accept.return_value = AttemptResponse.model_validate(
            self.example("attempt-queued")
        )
        repository.lookup.return_value = AttemptResponse.model_validate(
            self.example("attempt-succeeded")
        )
        command = self.example("provisioning-command")
        target = "src.modules.control_plane.presentation.router"
        with (
            patch(f"{target}.ProvisioningRepository", return_value=repository),
            patch(f"{target}.TenancyAdapter"),
            patch(
                f"{target}.instance_status",
                new=AsyncMock(
                    return_value=StatusResponse.model_validate(
                        self.example("status-two-zones")
                    )
                ),
            ),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(application),
                base_url="https://management.example.test",
            ) as client:
                accepted = await client.post(
                    "/internal/v1/tenant-provisioning/",
                    json=command,
                    headers={"Idempotency-Key": command["attempt_id"]},
                )
                self.assertEqual(accepted.status_code, 202)
                self.assertEqual(accepted.json(), self.example("attempt-queued"))
                unit_of_work.commit.assert_awaited_once()
                validated, digest, replay = repository.accept.call_args.args
                self.assertIsInstance(validated, ProvisioningCommand)
                self.assertEqual(len(digest), 64)
                self.assertNotIn(command["oidc"]["client_secret"], replay)
                result = await client.get(
                    f"/internal/v1/tenant-provisioning/{command['attempt_id']}/"
                )
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json(), self.example("attempt-succeeded"))
                status = await client.get("/internal/v1/status/")
                self.assertEqual(status.status_code, 200)
                self.assertEqual(status.json(), self.example("status-two-zones"))
                invalid = {**command, "protocol_version": 1}
                rejected = await client.post(
                    "/internal/v1/tenant-provisioning/",
                    json=invalid,
                    headers={"Idempotency-Key": command["attempt_id"]},
                )
                self.assertEqual(rejected.status_code, 422)
                self.assertNotIn(command["oidc"]["client_secret"], rejected.text)
