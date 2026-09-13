"""Transactional integration services. Callers own the Unit of Work."""

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.control_plane.application.contracts import (
    AttemptResponse,
    ProvisioningCommand,
)
from src.modules.control_plane.application.services import ProvisioningConflict
from src.modules.control_plane.infrastructure.crypto import CredentialCipher
from src.modules.control_plane.infrastructure.models import (
    AccessProjectionModel,
    CloudConnectionModel,
    DeliveryModel,
    InstallationModel,
    ProvisioningAttemptModel,
)


def now() -> datetime:
    return datetime.now(UTC)


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


async def serialize(session: AsyncSession, key: str) -> None:
    """Transaction advisory lock also serializes absent-row creation."""
    if session.get_bind().dialect.name == "postgresql":
        lock_id = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], signed=True)
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id}
        )


def response(
    attempt: ProvisioningAttemptModel, installation: InstallationModel
) -> AttemptResponse:
    return AttemptResponse(
        tenant_id=attempt.core_tenant_id,
        operation_id=attempt.operation_id,
        attempt_id=attempt.attempt_id,
        state=attempt.state,
        resources_state=attempt.resources_state,
        runtime_tenant_id=(
            str(installation.runtime_tenant_id)
            if attempt.resources_state == "present"
            else None
        ),
        error_code=attempt.error_code,
    )


class ProvisioningRepository:
    def __init__(self, session: AsyncSession, settings, resource_inspector=None):
        self.session = session
        self.settings = settings
        self.cipher = CredentialCipher(settings.secret_encryption_key)
        self.resource_inspector = resource_inspector

    async def accept(
        self, command: ProvisioningCommand, digest: str, replay_json: str
    ) -> AttemptResponse:
        # Immutable attempts can be replayed under MVCC without waiting for the
        # installer's DDL transaction/tenant lock. This keeps lost-response retries
        # responsive even while physical installation is running.
        saved = await self.session.get(ProvisioningAttemptModel, command.attempt_id)
        if saved is not None:
            installation = await self.session.get(InstallationModel, command.tenant_id)
            if saved.command_hash != digest or installation is None:
                raise ProvisioningConflict(
                    "Attempt identity conflicts with saved command"
                )
            return response(saved, installation)
        await serialize(self.session, f"cp:attempt:{command.attempt_id}")
        await serialize(self.session, f"cp:tenant:{command.tenant_id}")
        attempt = await self.session.get(ProvisioningAttemptModel, command.attempt_id)
        installation = await self.session.get(InstallationModel, command.tenant_id)
        if attempt is not None:
            if attempt.command_hash != digest or installation is None:
                raise ProvisioningConflict(
                    "Attempt identity conflicts with saved command"
                )
            return response(attempt, installation)

        if installation is not None:
            previous = await self.session.get(
                ProvisioningAttemptModel, installation.current_attempt_id
            )
            if installation.hostname != command.hostname:
                raise ProvisioningConflict("Tenant placement is immutable")
            if (
                previous is None
                or previous.state != "failed"
                or previous.resources_state != "absent"
            ):
                raise ProvisioningConflict(
                    "Previous installation is not confirmed absent"
                )
            # A recorded absence is not sufficient if resources appeared later.
            if (
                self.resource_inspector
                and await self.resource_inspector.inspect(
                    installation.runtime_tenant_id,
                    command.hostname,
                    str(command.tenant_id),
                )
                != "absent"
            ):
                raise ProvisioningConflict(
                    "Installation resources require reconciliation"
                )
        else:
            await serialize(self.session, f"cp:host:{command.hostname}")
            occupied = await self.session.scalar(
                select(InstallationModel).where(
                    InstallationModel.hostname == command.hostname
                )
            )
            if occupied is not None:
                raise ProvisioningConflict("Hostname is already reserved")
            runtime_id = uuid4()
            if (
                self.resource_inspector
                and await self.resource_inspector.inspect(
                    runtime_id, command.hostname, str(command.tenant_id)
                )
                != "absent"
            ):
                raise ProvisioningConflict("Existing resources require reconciliation")
            installation = InstallationModel(
                core_tenant_id=command.tenant_id,
                runtime_tenant_id=runtime_id,
                hostname=command.hostname,
                name=command.name,
                current_attempt_id=command.attempt_id,
                created_at=now(),
            )
            self.session.add(installation)

        connection = await self.session.get(
            CloudConnectionModel, installation.runtime_tenant_id
        )
        if connection is not None and connection.issuer != command.oidc.issuer:
            raise ProvisioningConflict("Tenant issuer is immutable")
        encrypted = self.cipher.encrypt(command.oidc.client_secret.get_secret_value())
        if connection is None:
            connection = CloudConnectionModel(
                runtime_tenant_id=installation.runtime_tenant_id,
                core_tenant_id=command.tenant_id,
            )
            self.session.add(connection)
        connection.issuer = command.oidc.issuer
        connection.client_id = command.oidc.client_id
        connection.callback = command.oidc.redirect_uri
        connection.encrypted_secret = encrypted
        installation.current_attempt_id = command.attempt_id
        installation.name = command.name
        stamp = now()
        attempt = ProvisioningAttemptModel(
            attempt_id=command.attempt_id,
            operation_id=command.operation_id,
            core_tenant_id=command.tenant_id,
            command_hash=digest,
            encrypted_command=self.cipher.encrypt(replay_json),
            state="queued",
            resources_state="absent",
            step="accepted",
            fencing_token=0,
            next_attempt_at=stamp,
            created_at=stamp,
            updated_at=stamp,
        )
        self.session.add(attempt)
        self.session.add(
            DeliveryModel(
                event_id=uuid4(),
                kind="install",
                aggregate_id=command.attempt_id,
                core_tenant_id=command.tenant_id,
                version=1,
                payload={"attempt_id": str(command.attempt_id)},
                state="pending",
                next_attempt_at=stamp,
                created_at=stamp,
            )
        )
        await self.session.flush()
        return response(attempt, installation)

    async def lookup(self, attempt_id: UUID) -> AttemptResponse | None:
        attempt = await self.session.get(ProvisioningAttemptModel, attempt_id)
        if attempt is None:
            return None
        installation = await self.session.get(InstallationModel, attempt.core_tenant_id)
        if installation is None:
            return None
        return response(attempt, installation)


class CloudConnectionReader:
    def __init__(self, session: AsyncSession, cipher: CredentialCipher | None = None):
        if cipher is None:
            from src.config import dnk_config

            cipher = CredentialCipher(dnk_config.CONTROL_PLANE.secret_encryption_key)
        self.session, self.cipher = session, cipher

    async def get(self, tenant_id: UUID):
        from src.modules.identity.application.ports.cloud import CloudConnection

        connection = await self.session.get(CloudConnectionModel, tenant_id)
        if connection is None:
            return None
        return CloudConnection(
            core_tenant_id=connection.core_tenant_id,
            issuer=connection.issuer,
            client_id=connection.client_id,
            callback=connection.callback,
            client_secret=self.cipher.decrypt(connection.encrypted_secret),
        )


class AccessProjectionWriter:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def set_available(
        self, tenant_id: UUID, global_user_id: UUID, available: bool
    ) -> int:
        installation = await self.session.scalar(
            select(InstallationModel).where(
                InstallationModel.runtime_tenant_id == tenant_id
            )
        )
        if installation is None:
            raise ValueError("Tenant has no cloud placement")
        core_id = installation.core_tenant_id
        await serialize(self.session, f"cp:access:{core_id}:{global_user_id}")
        projection = await self.session.get(
            AccessProjectionModel, (core_id, global_user_id)
        )
        if projection is not None and projection.available == available:
            return projection.version
        version = 1 if projection is None else projection.version + 1
        if version > 9223372036854775807:
            raise ValueError("Projection version exhausted")
        if projection is None:
            projection = AccessProjectionModel(
                core_tenant_id=core_id,
                global_user_id=global_user_id,
                available=available,
                version=version,
            )
            self.session.add(projection)
        else:
            projection.available, projection.version = available, version
        event_id, stamp = uuid4(), now()
        self.session.add(
            DeliveryModel(
                event_id=event_id,
                kind="access",
                aggregate_id=global_user_id,
                core_tenant_id=core_id,
                version=version,
                payload={
                    "event_id": str(event_id),
                    "version": version,
                    "available": available,
                },
                state="pending",
                next_attempt_at=stamp,
                created_at=stamp,
            )
        )
        await self.session.flush()
        return version
