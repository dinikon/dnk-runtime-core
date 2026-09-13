"""Public identity bootstrap adapter. No commit: caller owns installation UoW."""

from uuid import UUID

from src.config import dnk_config
from src.modules.identity.domain.user import UserIdVO
from src.modules.identity.infrastructure.repository.access_repository import (
    AccessRepository,
)
from src.modules.identity.infrastructure.repository.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)


async def bind_cloud_owner(
    session,
    tenant_id: UUID,
    user_id: UUID,
    issuer: str,
    subject: str,
    schema_prefix: str | None = None,
) -> None:
    # The contract defines Core sub as the global user UUID.
    UUID(subject)
    repo = AccessRepository(
        session, TenantSchemaNaming(schema_prefix or dnk_config.SCHEMA_PREFIX)
    )
    await repo.lock(tenant_id)
    await repo.bind(tenant_id, user_id, issuer, subject)


async def cloud_owner_ready(
    session,
    tenant_id: UUID,
    user_id: UUID,
    issuer: str,
    subject: str,
    schema_prefix: str | None = None,
) -> bool:
    naming = TenantSchemaNaming(schema_prefix or dnk_config.SCHEMA_PREFIX)
    repo = AccessRepository(session, naming)
    identity = await repo.identity_for_user(tenant_id, user_id)
    user = await SqlAlchemyUserRepository(session, naming).get_by_id(
        UserIdVO.from_value(user_id), tenant_id=EntityIdVO.from_value(tenant_id)
    )
    return bool(
        identity
        and identity.issuer == issuer
        and identity.subject == subject
        and user
        and user.can_login()
    )
