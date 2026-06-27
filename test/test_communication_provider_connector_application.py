from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.modules.communication.application.provider_connector import (
    DeleteProviderConnectorCommand,
    DeleteProviderConnectorUseCase,
    ListProviderConnectorsUseCase,
    ProviderConnectorDTO,
    ProviderMessageTypeDTO,
    RegisterProviderConnectorCommand,
    RegisterProviderConnectorUseCase,
    UpdateProviderConnectorStatusCommand,
    UpdateProviderConnectorStatusUseCase,
)
from src.modules.communication.application.services import ProviderYamlLoader
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderConnectorIdVO,
)
from src.modules.shared import EntityIdVO

VALID_PROVIDER_YAML = """
provider_code: gms
provider_name: GMS
version: "1.0.0"
connector_type: YAML_HTTP
channels:
  - SMS
message_types:
  - code: sms_text
    channel: SMS
    name: SMS text
    field_schema:
      type: object
    send:
      transport: http
      method: POST
      url: "https://example.test/send"
      body:
        text: "{{ template.text }}"
      response_mapping:
        external_message_id: "$.message_id"
        external_status: "$.status"
"""


class _ProviderConnectorServiceStub:
    def __init__(self, connector: ProviderConnector) -> None:
        self.connector = connector
        self.calls: list[dict[str, Any]] = []

    async def register_connector(self, **kwargs):
        self.calls.append(kwargs)
        return self.connector

    async def change_connector_status(self, **kwargs):
        self.calls.append(kwargs)
        self.connector.status = kwargs["status"].value
        return self.connector

    async def delete_connector(self, **kwargs):
        self.calls.append(kwargs)


class _QueryRepositoryStub:
    def __init__(
        self,
        connectors: list[ProviderConnectorDTO],
        message_types: list[ProviderMessageTypeDTO],
    ) -> None:
        self.connectors = connectors
        self.message_types = message_types
        self.connector_tenant_ids = []
        self.message_type_tenant_ids = []

    async def list_connectors(self, *, tenant_id):
        self.connector_tenant_ids.append(tenant_id)
        return self.connectors

    async def list_message_types(self, *, tenant_id):
        self.message_type_tenant_ids.append(tenant_id)
        return self.message_types


class ProviderConnectorApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_register_use_case_loads_yaml_and_returns_dto(self) -> None:
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        connector = ProviderConnector.create(
            provider_connector_id=provider_connector_id,
            provider_code="gms",
            provider_name="GMS",
            version="1.0.0",
            connector_type="YAML_HTTP",
            yaml_spec={
                "provider_code": "gms",
                "provider_name": "GMS",
                "version": "1.0.0",
                "connector_type": "YAML_HTTP",
                "channels": ["SMS"],
                "config_schema": {"type": "object"},
                "secrets_schema": {"type": "object"},
            },
            yaml_checksum="abc",
            now=now,
        )
        service = _ProviderConnectorServiceStub(connector)
        use_case = RegisterProviderConnectorUseCase(service, ProviderYamlLoader())

        result = await use_case(
            RegisterProviderConnectorCommand(
                tenant_id=tenant_id,
                provider_connector_id=provider_connector_id,
                yaml_content=VALID_PROVIDER_YAML,
            )
        )

        self.assertEqual(result.provider_connector_id, provider_connector_id.uuid)
        self.assertEqual(result.provider_code, "gms")
        self.assertEqual(result.channels, ["SMS"])
        self.assertEqual(service.calls[0]["tenant_id"], tenant_id)
        self.assertEqual(
            service.calls[0]["provider_connector_id"], provider_connector_id
        )
        self.assertEqual(
            service.calls[0]["spec"]["message_types"][0]["code"], "sms_text"
        )
        self.assertEqual(len(service.calls[0]["checksum"]), 64)

    async def test_list_use_case_returns_catalog_from_query_repository(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        connector = ProviderConnectorDTO(
            provider_connector_id=uuid4(),
            provider_code="gms",
            provider_name="GMS",
            version="1.0.0",
            connector_type="YAML_HTTP",
            channels=["SMS"],
            config_schema={},
            secrets_schema={},
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        message_type = ProviderMessageTypeDTO(
            provider_message_type_id=uuid4(),
            provider_connector_id=connector.provider_connector_id,
            message_type_code="sms_text",
            channel_code="SMS",
            name="SMS text",
            field_schema={},
            ui_schema={},
            is_active=True,
        )
        repository = _QueryRepositoryStub([connector], [message_type])
        use_case = ListProviderConnectorsUseCase(repository)

        result = await use_case(tenant_id)

        self.assertEqual(result.connectors, [connector])
        self.assertEqual(result.message_types, [message_type])
        self.assertEqual(repository.connector_tenant_ids, [tenant_id])
        self.assertEqual(repository.message_type_tenant_ids, [tenant_id])

    async def test_update_status_use_case_returns_dto(self) -> None:
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        connector = ProviderConnector.create(
            provider_connector_id=provider_connector_id,
            provider_code="gms",
            provider_name="GMS",
            version="1.0.0",
            connector_type="YAML_HTTP",
            yaml_spec={"channels": ["SMS"]},
            yaml_checksum="abc",
            now=now,
        )
        service = _ProviderConnectorServiceStub(connector)
        use_case = UpdateProviderConnectorStatusUseCase(service)

        result = await use_case(
            UpdateProviderConnectorStatusCommand(
                tenant_id=tenant_id,
                provider_connector_id=provider_connector_id,
                status="DISABLED",
            )
        )

        self.assertEqual(result.status, "DISABLED")
        self.assertEqual(
            service.calls[0]["provider_connector_id"], provider_connector_id
        )

    async def test_delete_use_case_delegates_to_service(self) -> None:
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        connector = ProviderConnector.create(
            provider_connector_id=provider_connector_id,
            provider_code="gms",
            provider_name="GMS",
            version="1.0.0",
            connector_type="YAML_HTTP",
            yaml_spec={"channels": ["SMS"]},
            yaml_checksum="abc",
            now=now,
        )
        service = _ProviderConnectorServiceStub(connector)
        use_case = DeleteProviderConnectorUseCase(service)

        await use_case(
            DeleteProviderConnectorCommand(
                tenant_id=tenant_id,
                provider_connector_id=provider_connector_id,
            )
        )

        self.assertEqual(service.calls[0]["tenant_id"], tenant_id)
        self.assertEqual(
            service.calls[0]["provider_connector_id"], provider_connector_id
        )


__all__ = ["ProviderConnectorApplicationTests"]
