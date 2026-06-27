from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.modules.communication.domain.provider_connector import (
    ConnectorStatus,
    InvalidProviderChannelCodeError,
    InvalidProviderConnectorCodeError,
    InvalidProviderConnectorNameError,
    InvalidProviderConnectorTypeError,
    InvalidProviderConnectorVersionError,
    InvalidProviderMessageTypeCodeError,
    InvalidProviderMessageTypeNameError,
    ProviderChannelCodeVO,
    ProviderConnector,
    ProviderConnectorArchivedError,
    ProviderConnectorCodeVO,
    ProviderConnectorDeleteForbiddenError,
    ProviderConnectorIdVO,
    ProviderConnectorInactiveError,
    ProviderConnectorNameVO,
    ProviderConnectorService,
    ProviderConnectorStatusTransitionError,
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

    def __init__(
        self,
        *,
        loaded: ProviderConnector | None = None,
        has_usage: bool = False,
    ) -> None:
        self.loaded = loaded
        self.has_usage_result = has_usage
        self.connector_calls: list[dict[str, Any]] = []
        self.message_type_calls: list[dict[str, Any]] = []
        self.deleted: list[ProviderConnectorIdVO] = []

    async def load_connector(self, **_kwargs):
        return self.loaded

    async def load_connector_by_code_version(self, **_kwargs):
        return self.loaded

    async def upsert_connector(self, **kwargs):
        self.connector_calls.append(kwargs)
        connector = ProviderConnector.create(
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
        self.loaded = connector
        return connector

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

    async def has_usage(self, *, tenant_id, provider_connector_id):
        return self.has_usage_result

    async def delete_connector(self, *, tenant_id, provider_connector_id):
        self.deleted.append(provider_connector_id)


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

    def test_entity_status_lifecycle_and_archive_are_guarded(self) -> None:
        created_at = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        updated_at = datetime(2026, 5, 13, 12, 5, tzinfo=UTC)
        connector = ProviderConnector.create(
            provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
            provider_code="gms",
            provider_name="GMS",
            version="1.0.0",
            connector_type="YAML_HTTP",
            yaml_spec={},
            yaml_checksum="abc",
            now=created_at,
        )

        connector.change_status(status=ConnectorStatus.DISABLED, now=updated_at)
        self.assertEqual(connector.status, ConnectorStatus.DISABLED.value)
        self.assertEqual(connector.updated_at, updated_at)

        same_status_updated_at = connector.updated_at
        connector.change_status(status=ConnectorStatus.DISABLED, now=created_at)
        self.assertEqual(connector.updated_at, same_status_updated_at)

        connector.change_status(status=ConnectorStatus.ACTIVE, now=created_at)
        with self.assertRaises(ProviderConnectorDeleteForbiddenError):
            connector.ensure_deletable()

        connector.change_status(status=ConnectorStatus.DISABLED, now=updated_at)
        connector.archive(now=created_at)
        self.assertEqual(connector.status, ConnectorStatus.ARCHIVED.value)
        with self.assertRaises(ProviderConnectorStatusTransitionError):
            connector.change_status(status=ConnectorStatus.ACTIVE, now=updated_at)
        with self.assertRaises(ProviderConnectorInactiveError):
            connector.ensure_active()

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

    async def test_service_register_preserves_disabled_and_rejects_archived(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        existing = ProviderConnector.create(
            provider_connector_id=provider_connector_id,
            provider_code="gms",
            provider_name="GMS",
            version="1.0.0",
            connector_type="YAML_HTTP",
            yaml_spec={},
            yaml_checksum="old",
            status=ConnectorStatus.DISABLED.value,
            now=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        )
        repository = _ProviderConnectorRepositoryStub(loaded=existing)
        service = ProviderConnectorService(repository=repository, clock=_ClockStub())

        connector = await service.register_connector(
            tenant_id=tenant_id,
            provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
            checksum="abc",
            spec={
                "provider_code": "gms",
                "provider_name": "GMS",
                "version": "1.0.0",
                "connector_type": "YAML_HTTP",
                "channels": ["SMS"],
                "message_types": [
                    {
                        "code": "sms_text",
                        "channel": "SMS",
                        "name": "SMS text",
                        "field_schema": {"type": "object"},
                    }
                ],
            },
        )

        self.assertEqual(connector.provider_connector_id, provider_connector_id)
        self.assertEqual(connector.status, ConnectorStatus.DISABLED.value)

        repository.loaded.status = ConnectorStatus.ARCHIVED.value
        with self.assertRaises(ProviderConnectorArchivedError):
            await service.register_connector(
                tenant_id=tenant_id,
                provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
                checksum="abc",
                spec={
                    "provider_code": "gms",
                    "provider_name": "GMS",
                    "version": "1.0.0",
                    "connector_type": "YAML_HTTP",
                    "channels": ["SMS"],
                    "message_types": [],
                },
            )

    async def test_service_changes_status_and_deletes_hard_or_soft(self) -> None:
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
            now=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        )
        repository = _ProviderConnectorRepositoryStub(loaded=connector)
        service = ProviderConnectorService(repository=repository, clock=_ClockStub())

        changed = await service.change_connector_status(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
            status=ConnectorStatus.DISABLED,
        )
        self.assertEqual(changed.status, ConnectorStatus.DISABLED.value)
        await service.delete_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )
        self.assertEqual(repository.deleted, [provider_connector_id])

        used_connector = ProviderConnector.create(
            provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
            provider_code="sms",
            provider_name="SMS",
            version="1.0.0",
            connector_type="YAML_HTTP",
            yaml_spec={"channels": ["SMS"]},
            yaml_checksum="abc",
            status=ConnectorStatus.DISABLED.value,
            now=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        )
        used_repository = _ProviderConnectorRepositoryStub(
            loaded=used_connector,
            has_usage=True,
        )
        used_service = ProviderConnectorService(
            repository=used_repository,
            clock=_ClockStub(),
        )

        await used_service.delete_connector(
            tenant_id=tenant_id,
            provider_connector_id=used_connector.provider_connector_id,
        )

        self.assertEqual(used_repository.deleted, [])
        self.assertEqual(used_repository.connector_calls[-1]["status"], "ARCHIVED")


__all__ = ["ProviderConnectorDomainTests"]
