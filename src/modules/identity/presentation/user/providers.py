from __future__ import annotations
from fastapi import Depends
from src.config import dnk_config
from src.modules.identity.domain.user.repository import UserRepositoryProtocol
from src.modules.identity.infrastructure.user.persistence.repository import (
    SqlAlchemyUserRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from typing import Annotated


def get_users_repository(uow: UoWDep) -> UserRepositoryProtocol:
    """Создает SQLAlchemy user repository для текущей UoW."""
    return SqlAlchemyUserRepository(
        uow.session, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    )


UsersRepositoryDep = Annotated[UserRepositoryProtocol, Depends(get_users_repository)]
