from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.provider_connection import (
    InvalidProviderConnectionCodeError,
    InvalidProviderConnectionNameError,
    ProviderConnectionCodeVO,
    ProviderConnectionEntity,
    ProviderConnectionIdVO,
    ProviderConnectionNameVO,
    ProviderConnectionService,
    ProviderConnectionStatusVO,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderConnectorIdVO,
    ProviderConnectorNotFoundError,
)
from src.modules.shared import EntityIdVO


class _ClockStub:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _ProviderLookupStub:
    def __init__(self, connector: ProviderConnector | None) -> None:
        self.connector = connector

    async def load_provider_connector(self, **_kwargs):
        return self.connector


class _ConnectionRepositoryStub:
    def __init__(self) -> None:
        self.saved: list[ProviderConnectionEntity] = []

    async def load(self, **_kwargs):
        return None

    async def save(self, *, tenant_id, connection):
        self.saved.append(connection)
        return connection

    async def find_active(self, **_kwargs):
        return None


class _SchemaValidatorStub:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc
        self.config_calls: list[tuple[dict[str, Any], Any]] = []
        self.secret_calls: list[tuple[dict[str, Any], Any]] = []

    def validate_provider_config(self, payload, schema) -> None:
        self.config_calls.append((payload, schema))
        if self.exc is not None:
            raise self.exc

    def validate_provider_secrets(self, payload, schema) -> None:
        self.secret_calls.append((payload, schema))
        if self.exc is not None:
            raise self.exc


def _connector(provider_connector_id: ProviderConnectorIdVO) -> ProviderConnector:
    now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
    return ProviderConnector(
        provider_connector_id=provider_connector_id,
        provider_code="gms",
        provider_name="GMS",
        version="1.0.0",
        connector_type="YAML_HTTP",
        yaml_spec={
            "channels": ["SMS"],
            "config_schema": {"type": "object"},
            "secrets_schema": {"type": "object"},
        },
        yaml_checksum="abc",
        status="ACTIVE",
        created_at=now,
        updated_at=now,
    )


class ProviderConnectionDomainTests(unittest.IsolatedAsyncioTestCase):
    def test_value_objects_trim_and_reject_empty_values(self) -> None:
        self.assertEqual(ProviderConnectionCodeVO("  sms_main  ").value, "sms_main")
        self.assertEqual(ProviderConnectionNameVO("  Main SMS  ").value, "Main SMS")

        with self.assertRaises(InvalidProviderConnectionCodeError):
            ProviderConnectionCodeVO(" ")
        with self.assertRaises(InvalidProviderConnectionNameError):
            ProviderConnectionNameVO("")

    def test_entity_create_sets_defaults_and_copies_config(self) -> None:
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        config = {"client_id": "abc"}

        entity = ProviderConnectionEntity.create(
            provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
            now=now,
            tenant_id=EntityIdVO.from_value(uuid4()),
            provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
            connection_code="  sms_main  ",
            connection_name=" Main SMS ",
            channel_code="SMS",
            config=config,
            secret_ref=None,
            secrets_b64="encoded",
        )

        config["client_id"] = "changed"

        self.assertEqual(entity.created_at, now)
        self.assertEqual(entity.updated_at, now)
        self.assertEqual(entity.connection_code.value, "sms_main")
        self.assertEqual(entity.connection_name.value, "Main SMS")
        self.assertEqual(entity.status, ProviderConnectionStatusVO.ACTIVE)
        self.assertEqual(entity.config, {"client_id": "abc"})

    async def test_service_creates_connection_after_connector_and_schema_checks(
        self,
    ) -> None:
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        provider_connection_id = ProviderConnectionIdVO.from_value(uuid4())
        repository = _ConnectionRepositoryStub()
        validator = _SchemaValidatorStub()
        service = ProviderConnectionService(
            command_repository=repository,
            provider_lookup=_ProviderLookupStub(_connector(provider_connector_id)),
            schema_validator=validator,
            clock=_ClockStub(now),
        )

        entity = await service.create_connection(
            tenant_id=tenant_id,
            provider_connection_id=provider_connection_id,
            provider_connector_id=provider_connector_id,
            connection_code="sms_main",
            connection_name="Main SMS",
            channel_code="SMS",
            config={"client_id": "abc"},
            secrets={"token": "secret"},
            secret_ref=None,
            secrets_b64="encoded",
        )

        self.assertEqual(entity.provider_connection_id, provider_connection_id)
        self.assertEqual(entity.created_at, now)
        self.assertEqual(repository.saved, [entity])
        self.assertEqual(validator.config_calls[0][0], {"client_id": "abc"})
        self.assertEqual(validator.secret_calls[0][0], {"token": "secret"})

    async def test_service_raises_when_connector_is_missing(self) -> None:
        service = ProviderConnectionService(
            command_repository=_ConnectionRepositoryStub(),
            provider_lookup=_ProviderLookupStub(None),
            schema_validator=_SchemaValidatorStub(),
            clock=_ClockStub(datetime(2026, 5, 13, 12, 0, tzinfo=UTC)),
        )

        with self.assertRaises(ProviderConnectorNotFoundError):
            await service.create_connection(
                tenant_id=EntityIdVO.from_value(uuid4()),
                provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
                provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
                connection_code="sms_main",
                connection_name="Main SMS",
                channel_code="SMS",
                config={},
                secrets={},
                secret_ref=None,
                secrets_b64=None,
            )

    async def test_service_rejects_unsupported_channel(self) -> None:
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        repository = _ConnectionRepositoryStub()
        service = ProviderConnectionService(
            command_repository=repository,
            provider_lookup=_ProviderLookupStub(_connector(provider_connector_id)),
            schema_validator=_SchemaValidatorStub(),
            clock=_ClockStub(datetime(2026, 5, 13, 12, 0, tzinfo=UTC)),
        )

        with self.assertRaises(CommunicationValidationError):
            await service.create_connection(
                tenant_id=EntityIdVO.from_value(uuid4()),
                provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
                provider_connector_id=provider_connector_id,
                connection_code="email_main",
                connection_name="Main Email",
                channel_code="EMAIL",
                config={},
                secrets={},
                secret_ref=None,
                secrets_b64=None,
            )

        self.assertEqual(repository.saved, [])

    async def test_service_propagates_schema_validation_error(self) -> None:
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        repository = _ConnectionRepositoryStub()
        service = ProviderConnectionService(
            command_repository=repository,
            provider_lookup=_ProviderLookupStub(_connector(provider_connector_id)),
            schema_validator=_SchemaValidatorStub(
                CommunicationValidationError("invalid config")
            ),
            clock=_ClockStub(datetime(2026, 5, 13, 12, 0, tzinfo=UTC)),
        )

        with self.assertRaises(CommunicationValidationError):
            await service.create_connection(
                tenant_id=EntityIdVO.from_value(uuid4()),
                provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
                provider_connector_id=provider_connector_id,
                connection_code="sms_main",
                connection_name="Main SMS",
                channel_code="SMS",
                config={},
                secrets={},
                secret_ref=None,
                secrets_b64=None,
            )

        self.assertEqual(repository.saved, [])


__all__ = ["ProviderConnectionDomainTests"]
