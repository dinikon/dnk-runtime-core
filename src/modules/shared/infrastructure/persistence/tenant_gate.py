"""Process-independent admission barrier spanning commits and external effects."""

import asyncio
import hashlib
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, async_sessionmaker

from src.modules.shared.application.persistence.tenant_admission import (
    TenantUnavailable,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel

DELETING = frozenset({"deletion_pending", "blocked", "purging", "deleted"})


def gate_key(tenant_id):
    return int.from_bytes(
        hashlib.sha256(f"dnk:tenant-admission:{tenant_id}".encode()).digest()[:8],
        signed=True,
    )


class TenantGate:
    def __init__(self, sessions):
        self.sessions = sessions

    @asynccontextmanager
    async def hold(self, tenant_id: UUID, *, exclusive=False, require_tenant=True):
        if tenant_id is None:
            yield
            return
        bind = self.sessions.kw["bind"]
        engine = bind.engine if isinstance(bind, AsyncConnection) else bind
        async with engine.connect() as connection:
            postgres = connection.dialect.name == "postgresql"
            key = gate_key(tenant_id)
            suffix = "" if exclusive else "_shared"
            acquired = False
            try:
                if postgres:
                    acquired = bool(
                        await connection.scalar(
                            text(f"SELECT pg_try_advisory_lock{suffix}(:key)"),
                            {"key": key},
                        )
                    )
                    if not acquired:
                        raise TenantUnavailable("Tenant has running operations.")
                if not exclusive and require_tenant:
                    state = await connection.scalar(
                        select(TenantModel.status).where(TenantModel.id == tenant_id)
                    )
                    if state is None or state in DELETING:
                        raise TenantUnavailable("Workspace unavailable.")
                # The connection remains checked out across every business
                # transaction. HTTP UoWs reuse it so admission cannot exhaust
                # the pool while all handlers wait for a second connection.
                await connection.commit()
                yield connection
            finally:
                if postgres and acquired:
                    try:
                        await connection.rollback()
                        await asyncio.shield(
                            connection.execute(
                                text(f"SELECT pg_advisory_unlock{suffix}(:key)"),
                                {"key": key},
                            )
                        )
                        await connection.commit()
                    except BaseException:
                        await connection.invalidate()
                        raise


def session_guard(session):
    """Protect external calls and the caller's final SQL commit."""
    gate = TenantGate(async_sessionmaker(session.bind, expire_on_commit=False))

    @asynccontextmanager
    async def guard(tenant_id):
        async with gate.hold(tenant_id):
            connection = await session.connection()
            if connection.dialect.name == "postgresql":
                # Acquiring cannot wait: our session lease already excludes purge.
                await connection.execute(
                    text("SELECT pg_advisory_xact_lock_shared(:key)"),
                    {"key": gate_key(tenant_id)},
                )
            yield

    return guard
