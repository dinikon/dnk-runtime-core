from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.provider_connection import (
    InvalidProviderConnectionNameError,
    ProviderConnectionDeleteForbiddenError,
    ProviderConnectionEntity,
    ProviderConnectionIdVO,
    ProviderConnectionInactiveError,
    ProviderConnectionNameVO,
    ProviderConnectionService,
    ProviderConnectionStatusTransitionError,
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

    def __init__(
        self,
        *,
        loaded: ProviderConnectionEntity | None = None,
        has_usage: bool = False,
    ) -> None:
        self.loaded = loaded
        self.has_usage_result = has_usage
        self.saved: list[ProviderConnectionEntity] = []
        self.deleted: list[ProviderConnectionIdVO] = []

    async def load(self, **_kwargs):
        return self.loaded

    async def save(self, *, tenant_id, connection):
        self.saved.append(connection)
        self.loaded = connection
        return connection

    async def find_active(self, **_kwargs):
        return None

    async def has_usage(self, *, tenant_id, provider_connection_id):
        return self.has_usage_result

    async def delete(self, *, tenant_id, provider_connection_id):
        self.deleted.append(provider_connection_id)


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


def _connector(
    provider_connector_id: ProviderConnectorIdVO,
    *,
    status: str = "ACTIVE",
) -> ProviderConnector:
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
        status=status,
        created_at=now,
        updated_at=now,
    )


class ProviderConnectionDomainTests(unittest.IsolatedAsyncioTestCase):
    def test_value_objects_trim_and_reject_empty_values(self) -> None:
        self.assertEqual(ProviderConnectionNameVO("  Main SMS  ").value, "Main SMS")

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
            connection_name=" Main SMS ",
            channel_code="SMS",
            config=config,
            secret_ref=None,
            secrets_b64="encoded",
        )

        config["client_id"] = "changed"

        self.assertEqual(entity.created_at, now)
        self.assertEqual(entity.updated_at, now)
        self.assertEqual(entity.connection_name.value, "Main SMS")
        self.assertEqual(entity.status, ProviderConnectionStatusVO.ACTIVE)
        self.assertEqual(entity.config, {"client_id": "abc"})

    def test_entity_status_lifecycle_and_archive_are_guarded(self) -> None:
        created_at = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        updated_at = datetime(2026, 5, 13, 12, 5, tzinfo=UTC)
        entity = ProviderConnectionEntity.create(
            provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
            now=created_at,
            tenant_id=EntityIdVO.from_value(uuid4()),
            provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
            connection_name="Main SMS",
            channel_code="SMS",
            config={},
            secret_ref=None,
            secrets_b64=None,
        )

        entity.change_status(status=ProviderConnectionStatusVO.DISABLED, now=updated_at)
        self.assertEqual(entity.status, ProviderConnectionStatusVO.DISABLED)
        self.assertEqual(entity.updated_at, updated_at)

        same_status_updated_at = entity.updated_at
        entity.change_status(status=ProviderConnectionStatusVO.DISABLED, now=created_at)
        self.assertEqual(entity.updated_at, same_status_updated_at)

        entity.change_status(status=ProviderConnectionStatusVO.ACTIVE, now=created_at)
        self.assertEqual(entity.status, ProviderConnectionStatusVO.ACTIVE)
        with self.assertRaises(ProviderConnectionDeleteForbiddenError):
            entity.ensure_deletable()

        entity.change_status(status=ProviderConnectionStatusVO.DISABLED, now=updated_at)
        entity.archive(now=created_at)
        self.assertEqual(entity.status, ProviderConnectionStatusVO.ARCHIVED)
        with self.assertRaises(ProviderConnectionStatusTransitionError):
            entity.change_status(
                status=ProviderConnectionStatusVO.ACTIVE, now=updated_at
            )
        with self.assertRaises(ProviderConnectionInactiveError):
            entity.ensure_active()

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
                connection_name="Main Email",
                channel_code="EMAIL",
                config={},
                secrets={},
                secret_ref=None,
                secrets_b64=None,
            )

        self.assertEqual(repository.saved, [])

    async def test_service_rejects_connection_for_disabled_connector(self) -> None:
        provider_connector_id = ProviderConnectorIdVO.from_value(uuid4())
        repository = _ConnectionRepositoryStub()
        service = ProviderConnectionService(
            command_repository=repository,
            provider_lookup=_ProviderLookupStub(
                _connector(provider_connector_id, status="DISABLED")
            ),
            schema_validator=_SchemaValidatorStub(),
            clock=_ClockStub(datetime(2026, 5, 13, 12, 0, tzinfo=UTC)),
        )

        with self.assertRaises(CommunicationValidationError):
            await service.create_connection(
                tenant_id=EntityIdVO.from_value(uuid4()),
                provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
                provider_connector_id=provider_connector_id,
                connection_name="Main SMS",
                channel_code="SMS",
                config={},
                secrets={},
                secret_ref=None,
                secrets_b64=None,
            )

        self.assertEqual(repository.saved, [])

    async def test_service_changes_status_and_deletes_hard_or_soft(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        provider_connection_id = ProviderConnectionIdVO.from_value(uuid4())
        now = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
        connection = ProviderConnectionEntity.create(
            provider_connection_id=provider_connection_id,
            now=now,
            tenant_id=tenant_id,
            provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
            connection_name="Main SMS",
            channel_code="SMS",
            config={},
            secret_ref=None,
            secrets_b64=None,
        )
        repository = _ConnectionRepositoryStub(loaded=connection)
        service = ProviderConnectionService(
            command_repository=repository,
            provider_lookup=_ProviderLookupStub(None),
            schema_validator=_SchemaValidatorStub(),
            clock=_ClockStub(now),
        )

        changed = await service.change_connection_status(
            tenant_id=tenant_id,
            provider_connection_id=provider_connection_id,
            status=ProviderConnectionStatusVO.DISABLED,
        )
        self.assertEqual(changed.status, ProviderConnectionStatusVO.DISABLED)
        await service.delete_connection(
            tenant_id=tenant_id,
            provider_connection_id=provider_connection_id,
        )
        self.assertEqual(repository.deleted, [provider_connection_id])

        used_connection = ProviderConnectionEntity.create(
            provider_connection_id=ProviderConnectionIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            provider_connector_id=ProviderConnectorIdVO.from_value(uuid4()),
            connection_name="Secondary SMS",
            channel_code="SMS",
            config={},
            secret_ref=None,
            secrets_b64=None,
            status=ProviderConnectionStatusVO.DISABLED,
        )
        used_repository = _ConnectionRepositoryStub(
            loaded=used_connection,
            has_usage=True,
        )
        used_service = ProviderConnectionService(
            command_repository=used_repository,
            provider_lookup=_ProviderLookupStub(None),
            schema_validator=_SchemaValidatorStub(),
            clock=_ClockStub(now),
        )

        await used_service.delete_connection(
            tenant_id=tenant_id,
            provider_connection_id=used_connection.provider_connection_id,
        )

        self.assertEqual(used_repository.deleted, [])
        self.assertEqual(
            used_repository.saved[-1].status,
            ProviderConnectionStatusVO.ARCHIVED,
        )

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
                connection_name="Main SMS",
                channel_code="SMS",
                config={},
                secrets={},
                secret_ref=None,
                secrets_b64=None,
            )

        self.assertEqual(repository.saved, [])


__all__ = ["ProviderConnectionDomainTests"]
