from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.modules.communication.domain.provider_connector import (
    InvalidProviderChannelCodeError,
    InvalidProviderConnectorCodeError,
    InvalidProviderConnectorNameError,
    InvalidProviderConnectorTypeError,
    InvalidProviderConnectorVersionError,
    InvalidProviderMessageTypeCodeError,
    InvalidProviderMessageTypeNameError,
    ProviderChannelCodeVO,
    ProviderConnector,
    ProviderConnectorCodeVO,
    ProviderConnectorIdVO,
    ProviderConnectorNameVO,
    ProviderConnectorService,
    ProviderConnectorVersionVO,
    ProviderMessageType,
    ProviderMessageTypeCodeVO,
    ProviderMessageTypeIdVO,
    ProviderMessageTypeNameVO,
)
from src.modules.shared import EntityIdVO


class _ClockStub:
    def now(self):
        return datetime(2026, 5, 13, 12, 0, tzinfo=UTC)


class _ProviderConnectorRepositoryStub:
    def __init__(self) -> None:
        self.connector_calls: list[dict[str, Any]] = []
        self.message_type_calls: list[dict[str, Any]] = []

    async def upsert_connector(self, **kwargs):
        self.connector_calls.append(kwargs)
        return ProviderConnector.create(
            provider_connector_id=kwargs["provider_connector_id"],
            provider_code=kwargs["provider_code"].value,
            provider_name=kwargs["provider_name"].value,
            version=kwargs["version"].value,
            connector_type=kwargs["connector_type"],
            yaml_spec=kwargs["yaml_spec"],
            yaml_checksum=kwargs["yaml_checksum"],
            status=kwargs["status"],
            now=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        )

    async def upsert_message_type(self, **kwargs):
        self.message_type_calls.append(kwargs)
        return ProviderMessageType.create(
            provider_message_type_id=ProviderMessageTypeIdVO.from_value(uuid4()),
            provider_connector_id=kwargs["provider_connector_id"],
            message_type_code=kwargs["message_type_code"].value,
            channel_code=kwargs["channel_code"].value,
            name=kwargs["name"].value,
            field_schema=kwargs["field_schema"],
            ui_schema=kwargs["ui_schema"],
            is_active=kwargs["is_active"],
        )


class ProviderConnectorDomainTests(unittest.IsolatedAsyncioTestCase):
    def test_value_objects_trim_and_reject_empty_values(self) -> None:
        self.assertEqual(ProviderConnectorCodeVO("  gms  ").value, "gms")
        self.assertEqual(ProviderConnectorNameVO("  GMS  ").value, "GMS")
        self.assertEqual(ProviderConnectorVersionVO("  1.0.0  ").value, "1.0.0")
        self.assertEqual(ProviderMessageTypeCodeVO("  sms_text  ").value, "sms_text")
        self.assertEqual(ProviderMessageTypeNameVO("  SMS text  ").value, "SMS text")
        self.assertEqual(ProviderChannelCodeVO("  SMS  ").value, "SMS")

        with self.assertRaises(InvalidProviderConnectorCodeError):
            ProviderConnectorCodeVO(" ")
        with self.assertRaises(InvalidProviderConnectorNameError):
            ProviderConnectorNameVO("")
        with self.assertRaises(InvalidProviderConnectorVersionError):
            ProviderConnectorVersionVO("")
        with self.assertRaises(InvalidProviderMessageTypeCodeError):
            ProviderMessageTypeCodeVO(" ")
        with self.assertRaises(InvalidProviderMessageTypeNameError):
            ProviderMessageTypeNameVO("")
        with self.assertRaises(InvalidProviderChannelCodeError):
            ProviderChannelCodeVO("")

    def test_entity_create_rejects_invalid_connector_type(self) -> None:
        with self.assertRaises(InvalidProviderConnectorTypeError):
            ProviderConnector.create(
                provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
                provider_code="gms",
                provider_name="GMS",
                version="1.0.0",
                connector_type="UNKNOWN",
                yaml_spec={},
                yaml_checksum="abc",
                now=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
            )

    async def test_service_registers_connector_and_message_types(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        repository = _ProviderConnectorRepositoryStub()
        service = ProviderConnectorService(
            repository=repository,
            clock=_ClockStub(),
        )

        connector = await service.register_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
            checksum="abc",
            spec={
                "provider_code": " gms ",
                "provider_name": " GMS ",
                "version": " 1.0.0 ",
                "connector_type": "YAML_HTTP",
                "channels": ["SMS"],
                "message_types": [
                    {
                        "code": " sms_text ",
                        "channel": " SMS ",
                        "name": " SMS text ",
                        "field_schema": {"type": "object"},
                    }
                ],
            },
        )

        self.assertEqual(connector.provider_connector_id, provider_connector_id)
        self.assertEqual(connector.provider_code, "gms")
        self.assertEqual(repository.connector_calls[0]["tenant_id"], tenant_id)
        self.assertIs(
            type(repository.connector_calls[0]["provider_code"]),
            ProviderConnectorCodeVO,
        )
        self.assertEqual(
            repository.message_type_calls[0]["message_type_code"].value,
            "sms_text",
        )
        self.assertEqual(repository.message_type_calls[0]["channel_code"].value, "SMS")


__all__ = ["ProviderConnectorDomainTests"]
