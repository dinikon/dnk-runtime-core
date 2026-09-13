"""All access changes share the caller's UoW and a tenant transaction lock."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, insert, update, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.access import IdentityAccessError
from src.modules.identity.application.ports.access import CloudIdentity, Invitation
from src.modules.identity.infrastructure.persistence.access import (
    CloudIdentityModel,
    InvitationModel,
)
from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.identity.infrastructure.persistence.user_email import UserEmailModel
from src.modules.shared import EntityIdVO
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS


class AccessRepository:
    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming):
        self.session, self.naming = session, naming

    def scoped(self, statement, tenant_id: UUID):
        return statement.execution_options(
            schema_translate_map={
                TENANT_SCHEMA_ALIAS: self.naming.schema_name(
                    EntityIdVO.from_value(tenant_id)
                )
            }
        )

    async def execute(self, statement, tenant_id: UUID):
        return await self.session.execute(self.scoped(statement, tenant_id))

    async def lock(self, tenant_id: UUID):
        # Separate namespace from provisioning; stable across Python processes.
        key = int.from_bytes(tenant_id.bytes[:8], "big", signed=True)
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": key}
        )

    async def identity_for_user(
        self, tenant_id: UUID, user_id: UUID
    ) -> CloudIdentity | None:
        table = CloudIdentityModel.__table__
        row = (
            (
                await self.execute(
                    select(table).where(table.c.user_id == user_id), tenant_id
                )
            )
            .mappings()
            .one_or_none()
        )
        return (
            CloudIdentity(row["user_id"], row["issuer"], row["subject"])
            if row
            else None
        )

    async def identity_for_subject(
        self, tenant_id: UUID, issuer: str, subject: str
    ) -> CloudIdentity | None:
        table = CloudIdentityModel.__table__
        row = (
            (
                await self.execute(
                    select(table).where(
                        table.c.issuer == issuer, table.c.subject == subject
                    ),
                    tenant_id,
                )
            )
            .mappings()
            .one_or_none()
        )
        return (
            CloudIdentity(row["user_id"], row["issuer"], row["subject"])
            if row
            else None
        )

    async def bind(self, tenant_id: UUID, user_id: UUID, issuer: str, subject: str):
        own = await self.identity_for_user(tenant_id, user_id)
        other = await self.identity_for_subject(tenant_id, issuer, subject)
        if own == CloudIdentity(user_id, issuer, subject):
            return
        if own or other:
            raise IdentityAccessError("Cloud account is already linked.", 409)
        await self.execute(
            insert(CloudIdentityModel.__table__).values(
                user_id=user_id,
                issuer=issuer,
                subject=subject,
                linked_at=datetime.now(UTC),
            ),
            tenant_id,
        )

    async def unbind(self, tenant_id: UUID, user_id: UUID):
        await self.execute(
            delete(CloudIdentityModel.__table__).where(
                CloudIdentityModel.user_id == user_id
            ),
            tenant_id,
        )
        users = UserModel.__table__
        await self.execute(
            update(users)
            .where(users.c.id == user_id)
            .values(
                session_epoch=users.c.session_epoch + 1, updated_at=datetime.now(UTC)
            ),
            tenant_id,
        )

    async def list_users(self, tenant_id: UUID):
        u, e, c = (
            UserModel.__table__,
            UserEmailModel.__table__,
            CloudIdentityModel.__table__,
        )
        rows = (
            (
                await self.execute(
                    select(
                        u.c.id,
                        u.c.first_name,
                        u.c.last_name,
                        u.c.role,
                        u.c.status,
                        e.c.email,
                        c.c.user_id.label("linked"),
                    )
                    .outerjoin(
                        e, (e.c.user_id == u.c.id) & e.c.is_primary & ~e.c.is_deleted
                    )
                    .outerjoin(c, c.c.user_id == u.c.id)
                    .order_by(u.c.created_at),
                    tenant_id,
                )
            )
            .mappings()
            .all()
        )
        return [
            dict(
                id=r["id"],
                first_name=r["first_name"],
                last_name=r["last_name"],
                role=r["role"],
                status=r["status"],
                email=r["email"],
                cloud_linked=r["linked"] is not None,
            )
            for r in rows
        ]

    async def change_access(
        self, tenant_id: UUID, user_id: UUID, role: str, status: str
    ):
        u = UserModel.__table__
        await self.execute(
            update(u)
            .where(u.c.id == user_id)
            .values(
                role=role,
                status=status,
                session_epoch=u.c.session_epoch + 1,
                updated_at=datetime.now(UTC),
            ),
            tenant_id,
        )

    async def active_admin_count(self, tenant_id: UUID) -> int:
        u = UserModel.__table__
        return (
            await self.execute(
                select(func.count())
                .select_from(u)
                .where(u.c.status == "active", u.c.role == "admin"),
                tenant_id,
            )
        ).scalar_one()

    async def add_invitation(self, tenant_id: UUID, invitation: Invitation):
        from dataclasses import asdict

        await self.execute(
            insert(InvitationModel.__table__).values(**asdict(invitation)), tenant_id
        )

    async def invitations(self, tenant_id: UUID):
        table = InvitationModel.__table__
        rows = (
            (
                await self.execute(
                    select(table).order_by(table.c.created_at.desc()), tenant_id
                )
            )
            .mappings()
            .all()
        )
        return [Invitation(**r) for r in rows]

    async def invitation(
        self,
        tenant_id: UUID,
        *,
        token_hash: str | None = None,
        invitation_id: UUID | None = None,
    ):
        table = InvitationModel.__table__
        query = select(table)
        query = (
            query.where(table.c.token_hash == token_hash)
            if token_hash is not None
            else query.where(table.c.id == invitation_id)
        )
        row = (await self.execute(query, tenant_id)).mappings().one_or_none()
        return Invitation(**row) if row else None

    async def finish_invitation(
        self,
        tenant_id: UUID,
        invitation_id: UUID,
        state: str,
        user_id: UUID | None = None,
    ):
        table = InvitationModel.__table__
        await self.execute(
            update(table)
            .where(table.c.id == invitation_id)
            .values(state=state, accepted_by=user_id),
            tenant_id,
        )
