"""Monotonic deletion state, transactional role checks and resumable erasure."""

import asyncio
import hashlib
import json
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.schema import DropSchema

from src.modules.control_plane.application.contracts import (
    DeletionCommand,
    DeletionResponse,
    DeletionCapability,
)
from src.modules.control_plane.infrastructure.models import (
    AccessProjectionModel,
    CloudConnectionModel,
    DeletionModel,
    DeliveryModel,
    InstallationModel,
    ProvisioningAttemptModel,
)
from src.modules.control_plane.infrastructure.services import (
    now,
    serialize,
    AccessProjectionWriter,
)
from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.identity.infrastructure.repository.access_repository import (
    AccessRepository,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence.tenant_gate import (
    TenantGate,
    TenantUnavailable,
)
from src.modules.shared.infrastructure.persistence.tenant_cleanup import (
    delete_shared_tenant_records,
)
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    lock_tenant_schema,
    schema_exists,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)


class DeletionError(Exception):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)


def deletion_response(row):
    return DeletionResponse(
        tenant_id=row.core_tenant_id,
        runtime_tenant_id=row.runtime_tenant_id,
        operation_id=row.operation_id,
        state=row.state,
        version=row.version,
        resources_state="absent" if row.state == "deleted" else "unknown",
        creation_succeeded=row.creation_succeeded,
        error_code=row.error_code,
    )


class DeletionRepository:
    def __init__(self, session, settings, schema_prefix):
        self.session, self.settings = session, settings
        self.naming = TenantSchemaNaming(schema_prefix)

    async def capability(self, tenant_id, user_id, authorization_basis):
        installation = await self.session.get(InstallationModel, tenant_id)
        if installation is None:
            return DeletionCapability(can_delete=False, reason="tenant_unavailable")
        tenant = await self.session.get(
            TenantModel, installation.runtime_tenant_id, populate_existing=True
        )
        if (
            tenant is None
            or tenant.external_id != str(tenant_id)
            or tenant.status not in {"active", "freeze"}
            or await self.session.get(DeletionModel, tenant_id)
        ):
            return DeletionCapability(can_delete=False, reason="tenant_unavailable")
        await AccessRepository(self.session, self.naming).lock(tenant.id)
        snapshot = await AccessProjectionWriter(self.session).refresh(
            installation,
            user_id,
            f"{self.settings.public_origin}/oidc/tenants/{tenant_id}",
            self.naming,
        )
        allowed = snapshot is not None and (
            authorization_basis == "owner"
            or (snapshot["available"] and snapshot["role"] == "admin")
        )
        return DeletionCapability(
            can_delete=allowed,
            reason=None if allowed else "administrator_required",
            access_snapshot=snapshot,
        )

    async def admin(self, tenant_id, user_id):
        installation = await self.session.get(InstallationModel, tenant_id)
        if installation is None:
            return False
        runtime_id = installation.runtime_tenant_id
        tenant = await self.session.get(TenantModel, runtime_id)
        if tenant is None or tenant.status not in {"active", "freeze"}:
            return False
        if not await schema_exists(
            await self.session.connection(),
            self.naming.schema_name(EntityIdVO.from_value(runtime_id)),
        ):
            return False
        access = AccessRepository(self.session, self.naming)
        binding = await access.identity_for_subject(
            runtime_id,
            f"{self.settings.public_origin}/oidc/tenants/{tenant_id}",
            str(user_id),
        )
        if binding is None:
            return False
        users = UserModel.__table__
        return bool(
            (
                await access.execute(
                    select(users.c.id).where(
                        users.c.id == binding.user_id,
                        users.c.role == "admin",
                        users.c.status == "active",
                    ),
                    runtime_id,
                )
            ).scalar_one_or_none()
        )

    async def lookup(self, operation_id):
        row = await self.session.scalar(
            select(DeletionModel).where(DeletionModel.operation_id == operation_id)
        )
        return deletion_response(row) if row else None

    async def accept(self, command: DeletionCommand):
        payload = command.model_dump(mode="json")
        # Keep the digest of pre-upgrade accepted commands, including tombstones.
        if command.authorization_basis == "runtime_admin":
            payload.pop("authorization_basis")
        command_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        await serialize(self.session, f"cp:tenant:{command.tenant_id}")
        saved = await self.session.get(
            DeletionModel, command.tenant_id, populate_existing=True
        )
        if saved:
            if saved.operation_id != command.operation_id:
                raise DeletionError("deletion_already_started")
            if saved.command_hash != command_hash:
                raise DeletionError("command_conflict")
            return deletion_response(saved)
        duplicate = await self.session.scalar(
            select(DeletionModel).where(
                DeletionModel.operation_id == command.operation_id
            )
        )
        if duplicate:
            raise DeletionError("command_conflict")
        installation = await self.session.get(InstallationModel, command.tenant_id)
        tenant = await self.session.scalar(
            select(TenantModel).where(TenantModel.external_id == str(command.tenant_id))
        )
        runtime_id = (
            installation.runtime_tenant_id
            if installation
            else (tenant.id if tenant else None)
        )
        if installation and installation.hostname != command.hostname:
            raise DeletionError("placement_conflict")
        if (
            command.runtime_tenant_id is not None
            and command.runtime_tenant_id != runtime_id
        ):
            raise DeletionError("placement_conflict")
        if tenant is not None and runtime_id != tenant.id:
            raise DeletionError("placement_conflict")
        target = await self.session.get(TenantModel, runtime_id) if runtime_id else None
        if target is not None and target.external_id != str(command.tenant_id):
            raise DeletionError("placement_conflict")
        host = await self.session.scalar(
            select(TenantDomainModel).where(TenantDomainModel.host == command.hostname)
        )
        if host is not None and host.tenant_id != runtime_id:
            raise DeletionError("placement_conflict")
        if runtime_id:
            # Membership changes use this exact lock. Commit of acceptance is
            # the authority boundary; capability lookups never grant a right.
            await AccessRepository(self.session, self.naming).lock(runtime_id)
        if command.source == "user":
            if command.authorization_basis == "owner":
                if tenant is None or tenant.status not in {"active", "freeze"}:
                    raise DeletionError("administrator_required", 403)
            elif not await self.admin(command.tenant_id, command.initiator_id):
                raise DeletionError("administrator_required", 403)
        created = bool(tenant and tenant.status in {"active", "freeze"}) or bool(
            await self.session.scalar(
                select(ProvisioningAttemptModel.attempt_id)
                .where(
                    ProvisioningAttemptModel.core_tenant_id == command.tenant_id,
                    ProvisioningAttemptModel.state == "succeeded",
                )
                .limit(1)
            )
        )
        row = DeletionModel(
            core_tenant_id=command.tenant_id,
            runtime_tenant_id=runtime_id,
            operation_id=command.operation_id,
            state="deletion_pending",
            version=1,
            command=payload,
            updated_at=now(),
            command_hash=command_hash,
            creation_succeeded=created,
        )
        self.session.add(row)
        if runtime_id:
            await self.session.execute(
                update(TenantModel)
                .where(TenantModel.id == runtime_id)
                .values(status="deletion_pending")
            )
        # Claim, execute and acceptance of provisioning all share cp:tenant.
        await self.session.execute(
            update(ProvisioningAttemptModel)
            .where(
                ProvisioningAttemptModel.core_tenant_id == command.tenant_id,
            )
            .values(
                fencing_token=ProvisioningAttemptModel.fencing_token + 1,
                lease_until=None,
            )
        )
        await self.session.flush()
        return deletion_response(row)

    async def request_purge(self, operation_id, command):
        row = await self.session.scalar(
            select(DeletionModel).where(DeletionModel.operation_id == operation_id)
        )
        if row is None:
            raise DeletionError("deletion_not_found", 404)
        await serialize(self.session, f"cp:tenant:{row.core_tenant_id}")
        await self.session.refresh(row)
        if command.tenant_id != row.core_tenant_id:
            raise DeletionError("command_conflict")
        if row.state in {"purging", "deleted"}:
            if command.version != 2:
                raise DeletionError("version_conflict")
            return deletion_response(row)
        if row.state != "blocked" or command.version != row.version:
            raise DeletionError("tenant_not_blocked")
        row.state, row.version, row.updated_at = "purging", 3, now()
        if row.runtime_tenant_id:
            await self.session.execute(
                update(TenantModel)
                .where(TenantModel.id == row.runtime_tenant_id)
                .values(status="purging")
            )
        return deletion_response(row)


async def erase_tokens(runtime_id, hosts):
    from src.modules.shared.infrastructure.tokens.redis_token_repository import (
        RedisTokenRepository,
    )

    repository = RedisTokenRepository.from_config()
    client = repository._client
    patterns = (
        [
            f"{prefix}:{runtime_id}:*"
            for prefix in ("session", "otp_login", "oidc_state", "invitation_otp")
        ]
        if runtime_id
        else []
    )
    patterns.extend(f"csrf:{host}:*" for host in hosts)
    try:
        for pattern in patterns:
            batch = []
            async for key in client.scan_iter(match=pattern, count=200):
                batch.append(key)
                if len(batch) == 200:
                    await client.unlink(*batch)
                    batch.clear()
            if batch:
                await client.unlink(*batch)
    finally:
        await client.aclose()


class DeletionWorker:
    def __init__(self, sessions, settings, schema_prefix, token_eraser=erase_tokens):
        self.sessions, self.settings = sessions, settings
        self.naming = TenantSchemaNaming(schema_prefix)
        self.token_eraser = token_eraser

    async def due(self):
        async with self.sessions() as session, session.begin():
            ids = list(
                await session.scalars(
                    select(DeletionModel.operation_id)
                    .where(DeletionModel.state.in_(["deletion_pending", "purging"]))
                    .order_by(DeletionModel.updated_at)
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
            )
            if ids:
                # Busy tenants must not indefinitely occupy the first batch
                # while unrelated tenants wait for their own admission drain.
                await session.execute(
                    update(DeletionModel)
                    .where(DeletionModel.operation_id.in_(ids))
                    .values(updated_at=now())
                )
        for operation_id in ids:
            await self.run(operation_id)

    async def run(self, operation_id):
        try:
            async with asyncio.timeout(self.settings.step_timeout_seconds):
                async with self.sessions() as session:
                    row = await session.scalar(
                        select(DeletionModel).where(
                            DeletionModel.operation_id == operation_id
                        )
                    )
                    if row is None or row.state not in {"deletion_pending", "purging"}:
                        return
                    runtime_id = row.runtime_tenant_id
                async with TenantGate(self.sessions).hold(runtime_id, exclusive=True):
                    async with self.sessions() as session, session.begin():
                        row = await session.scalar(
                            select(DeletionModel).where(
                                DeletionModel.operation_id == operation_id
                            )
                        )
                        if row is None:
                            return
                        await serialize(session, f"cp:tenant:{row.core_tenant_id}")
                        await session.refresh(row)
                        if row.state == "deletion_pending":
                            row.state, row.version, row.updated_at, row.error_code = (
                                "blocked",
                                2,
                                now(),
                                None,
                            )
                            if runtime_id:
                                await session.execute(
                                    update(TenantModel)
                                    .where(TenantModel.id == runtime_id)
                                    .values(status="blocked")
                                )
                        elif row.state == "purging":
                            await self.purge(session, row)
        except TenantUnavailable:
            # Busy requests drain naturally; no accepted block is undone.
            return
        except Exception:
            async with self.sessions() as session, session.begin():
                await session.execute(
                    update(DeletionModel)
                    .where(
                        DeletionModel.operation_id == operation_id,
                        DeletionModel.state.in_(["deletion_pending", "purging"]),
                    )
                    .values(error_code="deletion_step_failed", updated_at=now())
                )

    async def purge(self, session, row):
        runtime_id = row.runtime_tenant_id
        hosts = (
            list(
                await session.scalars(
                    select(TenantDomainModel.host).where(
                        TenantDomainModel.tenant_id == runtime_id
                    )
                )
            )
            if runtime_id
            else []
        )
        if row.command:
            hosts.append(row.command["hostname"])
        await self.token_eraser(runtime_id, set(hosts))
        if runtime_id:
            schema = self.naming.schema_name(EntityIdVO.from_value(runtime_id))
            connection = await session.connection()
            await lock_tenant_schema(connection, schema)
            await connection.execute(DropSchema(schema, cascade=True, if_exists=True))
            await delete_shared_tenant_records(session, runtime_id)
            await session.execute(
                delete(TenantDomainModel).where(
                    TenantDomainModel.tenant_id == runtime_id
                )
            )
            await session.execute(
                delete(TenantModel).where(TenantModel.id == runtime_id)
            )
        for model in (
            DeliveryModel,
            AccessProjectionModel,
            CloudConnectionModel,
            ProvisioningAttemptModel,
            InstallationModel,
        ):
            await session.execute(
                delete(model).where(model.core_tenant_id == row.core_tenant_id)
            )
        row.state, row.version, row.command, row.error_code, row.updated_at = (
            "deleted",
            4,
            None,
            None,
            now(),
        )
