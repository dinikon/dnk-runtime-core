from __future__ import annotations
from fastapi import Depends, HTTPException
from src.config import dnk_config
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.application.user.port.currency_validator import (
    ProfileCurrencyValidatorProtocol,
)
from src.modules.identity.application.user.port.tenant_currency_settings import (
    ProfileTenantCurrencySettingsProtocol,
)
from src.modules.identity.application.user.port.query_repository import (
    UserProfileQueryRepositoryProtocol,
)
from src.modules.identity.infrastructure.user.currency_validator import (
    ReferenceDataProfileCurrencyValidator,
)
from src.modules.identity.infrastructure.user.tenant_currency_settings import (
    TenancyProfileCurrencySettingsAdapter,
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
from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.handler import (
    GetTenantCurrencySettingsHandler,
)
from src.modules.tenancy.infrastructure.tenant_currency_settings.persistence.query_repository import (
    SqlAlchemyTenantCurrencySettingsQueryRepository,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
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


def get_profile_tenant_currency_settings(
    uow: UoWDep,
    context: AuthenticatedRequestContextDep,
) -> ProfileTenantCurrencySettingsProtocol:
    """Подключает публичный Query Tenancy к общей сессии доверенного Tenant."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant context is required.")
    return TenancyProfileCurrencySettingsAdapter(
        GetTenantCurrencySettingsHandler(
            SqlAlchemyTenantCurrencySettingsQueryRepository(
                uow.session, TenantIdVO.from_value(principal.tenant_id)
            )
        )
    )


ProfileTenantCurrencySettingsDep = Annotated[
    ProfileTenantCurrencySettingsProtocol, Depends(get_profile_tenant_currency_settings)
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
    settings: ProfileTenantCurrencySettingsDep,
) -> GetCurrentUserHandler:
    """Собирает сценарий чтения только из портов проекции и настроек Tenant."""
    return GetCurrentUserHandler(repository, settings)


GetCurrentUserHandlerDep = Annotated[
    GetCurrentUserHandler, Depends(get_current_user_handler)
]


def get_update_current_user_profile_handler(
    users_repository: UsersRepositoryDep,
    currency_validator: ProfileCurrencyValidatorDep,
    settings: ProfileTenantCurrencySettingsDep,
) -> UpdateCurrentUserProfileHandler:
    """Собирает обновление профиля; транзакцией управляет общий внешний UoW."""
    return UpdateCurrentUserProfileHandler(
        users_repository, currency_validator, settings
    )


UpdateCurrentUserProfileHandlerDep = Annotated[
    UpdateCurrentUserProfileHandler, Depends(get_update_current_user_profile_handler)
]
