from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.communication.application.provider_connection import (
    CreateProviderConnectionCommand,
    CreateProviderConnectionUseCase,
    ListProviderConnectionsUseCase,
    ProviderConnectionDTO,
)
from src.modules.communication.application.services import SecretCodec
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionEntity,
    ProviderConnectionIdVO,
)
from src.modules.communication.domain.provider_connector import ProviderConnectorIdVO
from src.modules.shared import EntityIdVO


class _ProviderConnectionServiceStub:
    def __init__(self, entity: ProviderConnectionEntity) -> None:
        self.entity = entity
        self.calls = []

    async def create_connection(self, **kwargs):
        self.calls.append(kwargs)
        return self.entity


class _QueryRepositoryStub:
    def __init__(self, items: list[ProviderConnectionDTO]) -> None:
        self.items = items
        self.tenant_ids = []

    async def list_connections(self, *, tenant_id):
        self.tenant_ids.append(tenant_id)
        return self.items


class ProviderConnectionApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_use_case_encodes_secrets_and_returns_dto_without_value(
        self,
    ) -> None:
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connection_id = ProviderConnectionIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        entity = ProviderConnectionEntity.create(
            provider_connection_id=provider_connection_id,
            now=now,
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
            connection_code="sms_main",
            connection_name="Main SMS",
            channel_code="SMS",
            config={"client_id": "abc"},
            secret_ref=None,
            secrets_b64=SecretCodec().encode({"token": "secret"}),
        )
        service = _ProviderConnectionServiceStub(entity)
        use_case = CreateProviderConnectionUseCase(
            service=service,
            secret_codec=SecretCodec(),
        )

        result = await use_case(
            CreateProviderConnectionCommand(
                tenant_id=tenant_id,
                provider_connection_id=provider_connection_id,
                provider_connector_id=provider_connector_id,
                connection_code="sms_main",
                connection_name="Main SMS",
                channel_code="SMS",
                config={"client_id": "abc"},
                secrets={"token": "secret"},
            )
        )

        self.assertEqual(result.provider_connection_id, provider_connection_id.uuid)
        self.assertEqual(result.connection_code, "sms_main")
        self.assertTrue(result.has_secrets)
        self.assertNotIn("secret", str(result))
        self.assertEqual(service.calls[0]["secrets"], {"token": "secret"})
        self.assertNotIn("secret", service.calls[0]["secrets_b64"] or "")

    async def test_list_use_case_returns_dto_from_query_repository(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        dto = ProviderConnectionDTO(
            provider_connection_id=uuid4(),
            tenant_id=tenant_id.uuid,
            provider_connector_id=uuid4(),
            connection_code="sms_main",
            connection_name="Main SMS",
            channel_code="SMS",
            config={},
            secret_ref=None,
            has_secrets=False,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        repository = _QueryRepositoryStub([dto])
        use_case = ListProviderConnectionsUseCase(repository)

        result = await use_case(tenant_id)

        self.assertEqual(result, [dto])
        self.assertEqual(repository.tenant_ids, [tenant_id])


__all__ = ["ProviderConnectionApplicationTests"]
