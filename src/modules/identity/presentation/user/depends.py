from __future__ import annotations
from fastapi import Depends
from src.config import dnk_config
from src.modules.identity.application.user.port.currency_validator import (
    ProfileCurrencyValidatorProtocol,
)
from src.modules.identity.application.user.port.query_repository import (
    UserProfileQueryRepositoryProtocol,
)
from src.modules.identity.infrastructure.user.currency_validator import (
    ReferenceDataProfileCurrencyValidator,
)
from src.modules.identity.infrastructure.user.persistence.query_repository import (
    SqlAlchemyUserProfileQueryRepository,
)
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.infrastructure.currency.persistence.query_repository import (
    SqlAlchemyCurrencyQueryRepository,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.identity.application.user.command.create_tenant_admin.handler import (
    CreateTenantAdminHandler,
)
from src.modules.identity.application.user.command.update_current_user_profile.handler import (
    UpdateCurrentUserProfileHandler,
)
from src.modules.identity.application.user.query.get_current_user.handler import (
    GetCurrentUserHandler,
)
from src.modules.identity.presentation.user.providers import UsersRepositoryDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from typing import Annotated


def get_create_tenant_admin_handler(
    users_repository: UsersRepositoryDep,
) -> CreateTenantAdminHandler:
    """Создает provisioning user service."""
    return CreateTenantAdminHandler(users_repository)


CreateTenantAdminHandlerDep = Annotated[
    CreateTenantAdminHandler, Depends(get_create_tenant_admin_handler)
]


def get_profile_currency_validator(uow: UoWDep) -> ProfileCurrencyValidatorProtocol:
    """Собирает проверку Reference Data на сессии текущего процесса профиля."""
    return ReferenceDataProfileCurrencyValidator(
        ValidateCurrencyHandler(SqlAlchemyCurrencyQueryRepository(uow.session))
    )


ProfileCurrencyValidatorDep = Annotated[
    ProfileCurrencyValidatorProtocol, Depends(get_profile_currency_validator)
]


def get_user_profile_query_repository(
    uow: UoWDep,
) -> UserProfileQueryRepositoryProtocol:
    """Создаёт отдельный репозиторий проекции профиля в tenant-схеме."""
    return SqlAlchemyUserProfileQueryRepository(
        uow.session, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    )


UserProfileQueryRepositoryDep = Annotated[
    UserProfileQueryRepositoryProtocol, Depends(get_user_profile_query_repository)
]


def get_current_user_handler(
    repository: UserProfileQueryRepositoryDep,
) -> GetCurrentUserHandler:
    """Собирает сценарий чтения только из порта проекции профиля."""
    return GetCurrentUserHandler(repository)


GetCurrentUserHandlerDep = Annotated[
    GetCurrentUserHandler, Depends(get_current_user_handler)
]


def get_update_current_user_profile_handler(
    users_repository: UsersRepositoryDep,
    currency_validator: ProfileCurrencyValidatorDep,
) -> UpdateCurrentUserProfileHandler:
    """Собирает обновление профиля; транзакцией управляет общий внешний UoW."""
    return UpdateCurrentUserProfileHandler(users_repository, currency_validator)


UpdateCurrentUserProfileHandlerDep = Annotated[
    UpdateCurrentUserProfileHandler, Depends(get_update_current_user_profile_handler)
]
