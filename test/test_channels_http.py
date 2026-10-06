"""HTTP-контракты с реальными Depends, UoW, authentication и CSRF."""

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from httpx import ASGITransport, AsyncClient
from cryptography.fernet import Fernet
from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.presentation.channel.depends import get_cipher
from src.modules.channels.infrastructure.channel.crypto.cipher import (
    ChannelSecretCipher,
)
from test.channels_support import channel_app
from src.modules.channels.presentation.publication_import_run.depends import (
    get_import_starter,
)


class ChannelsHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tenant, self.actor, self.identifier = uuid4(), uuid4(), uuid4()
        self.now = datetime(2026, 10, 6, tzinfo=UTC)
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.session = SimpleNamespace(
            execute=AsyncMock(),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        self.app = channel_app(lambda: self.session, self.context)
        self.imports = Mock(start=AsyncMock())
        self.app.dependency_overrides[get_import_starter] = lambda: self.imports
        self.app.state.clock = Mock(now=Mock(return_value=self.now))
        self.app.state.uuid_generator = Mock(new=Mock(return_value=self.identifier))
        self.cipher = ChannelSecretCipher(Fernet.generate_key().decode())
        self.app.dependency_overrides[get_cipher] = lambda: self.cipher
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=f"{scheme}://tenant.example",
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": f"{scheme}://tenant.example", "X-CSRF-Token": token}
        self.base = "/api/console/channels"
        self.payload = dict(
            name="Main",
            kind="prom",
            config_version=1,
            connection_settings={"api_key": "never-return-this"},
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    def public_row(self):
        return dict(
            id=self.identifier,
            name="Main",
            kind="prom",
            config_version=1,
            connection_settings={},
            configured_secret_fields=["api_key"],
            is_active=True,
            status="unverified",
            created_at=self.now,
            updated_at=self.now,
            created_by=self.actor,
            updated_by=self.actor,
        )

    async def test_catalog_and_schemas_require_no_database(self):
        response = await self.client.get(self.base + "/kinds")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()), 21)
        response = await self.client.get(self.base + "/kinds/woocommerce/config")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.json()["config"]["connection"]["json_schema"]["properties"][
                "consumer_key"
            ]["writeOnly"]
        )
        self.session.execute.assert_not_awaited()
        self.assertEqual(
            (await self.client.get(self.base + "/kinds/unknown/config")).status_code,
            404,
        )

    async def test_create_encrypts_and_returns_only_safe_projection(self):
        self.session.execute.return_value = Mock()
        response = await self.client.post(
            self.base, json=self.payload, headers=self.headers
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertNotIn("never-return-this", response.text)
        self.assertEqual(response.json()["configured_secret_fields"], ["api_key"])
        statement = self.session.execute.call_args_list[0].args[0]
        params = statement.compile().params
        self.assertNotIn("never-return-this", repr(params))
        self.assertEqual(
            self.cipher.decrypt(params["encrypted_secrets"]),
            self.payload["connection_settings"],
        )
        self.session.execute.assert_awaited_once()
        self.session.commit.assert_awaited_once()

    async def test_invalid_requests_never_echo_secret_or_write(self):
        payloads = [
            self.payload | {"config_version": 3},
            self.payload | {"is_active": "yes"},
            self.payload | {"tenant_id": str(uuid4())},
            self.payload | {"kind": "shopify"},
            self.payload | {"connection_settings": {"api_key": ""}},
            self.payload
            | {
                "connection_settings": {
                    "api_key": "never-return-this",
                    "other": "never-return-this",
                }
            },
        ]
        for payload in payloads:
            response = await self.client.post(
                self.base, json=payload, headers=self.headers
            )
            self.assertIn(response.status_code, (409, 422), response.text)
            self.assertNotIn("never-return-this", response.text)
        self.session.execute.assert_not_awaited()

    async def test_null_patch_and_status_are_rejected(self):
        for payload in [
            {"name": None},
            {"status": "connected"},
            {"kind": "woocommerce"},
            {"connection_settings": {}},
            {},
            {"is_active": 1},
        ]:
            response = await self.client.patch(
                self.base + "/" + str(self.identifier),
                json=payload,
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 422, response.text)
        self.session.execute.assert_not_awaited()

    async def test_secrets_unavailable_does_not_write(self):
        self.app.dependency_overrides[get_cipher] = lambda: ChannelSecretCipher("")
        response = await self.client.post(
            self.base, json=self.payload, headers=self.headers
        )
        self.assertEqual(response.status_code, 503, response.text)
        self.assertNotIn("never-return-this", response.text)
        self.session.execute.assert_not_awaited()
        self.session.rollback.assert_awaited_once()

    async def test_auth_csrf_and_not_found(self):
        response = await self.client.post(self.base, json=self.payload)
        self.assertIn(response.status_code, (401, 403))
        self.session.execute.return_value = Mock(
            mappings=Mock(return_value=Mock(one_or_none=Mock(return_value=None)))
        )
        self.assertEqual(
            (await self.client.get(self.base + "/" + str(self.identifier))).status_code,
            404,
        )
        self.app.state.test_context = RequestContext(None, None, None, None)
        self.assertEqual((await self.client.get(self.base + "/kinds")).status_code, 401)

    async def test_endpoint_schemas_are_independent(self):
        schemas = self.app.openapi()["components"]["schemas"]
        self.assertTrue(
            {
                "CreateChannelResponse",
                "UpdateChannelResponse",
                "GetChannelResponse",
                "ListChannelItemResponse",
                "ListChannelKindItemResponse",
                "GetKindConfigResponse",
            }
            <= schemas.keys()
        )
        self.assertNotIn("ChannelResponse", schemas)

    async def test_create_returns_only_after_commit_and_commit_failure_is_not_success(
        self,
    ):
        self.session.execute.return_value = Mock()
        self.session.commit.side_effect = RuntimeError("test commit failure")
        with self.assertLogs(
            "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
            level="ERROR",
        ):
            response = await self.client.post(
                self.base, json=self.payload, headers=self.headers
            )
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("never-return-this", response.text)
        self.session.close.assert_awaited()

    async def test_names_are_validated_after_trimming(self):
        self.session.execute.return_value = Mock()
        response = await self.client.post(
            self.base,
            json=self.payload | {"name": "  " + "x" * 255 + "  "},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["name"], "x" * 255)
        response = await self.client.post(
            self.base,
            json=self.payload | {"name": "  "},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"][0]["loc"], ["body", "name"])

    async def test_schema_error_paths_and_messages_never_echo_credentials(self):
        response = await self.client.post(
            self.base,
            json=self.payload | {"connection_settings": {"api_key": ""}},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"][0]["loc"],
            ["body", "connection_settings", "api_key"],
        )
        self.assertEqual(set(response.json()["detail"][0]), {"loc", "msg", "type"})
