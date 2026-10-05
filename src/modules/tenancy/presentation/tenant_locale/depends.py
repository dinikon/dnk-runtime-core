from typing import Annotated

from fastapi import Depends

from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.tenancy.application.tenant_locale.command.add_tenant_locale.handler import (
    AddTenantLocaleHandler,
)
from src.modules.tenancy.application.tenant_locale.command.remove_tenant_locale.handler import (
    RemoveTenantLocaleHandler,
)
from src.modules.tenancy.application.tenant_locale.port.query_repository import (
    TenantLocaleQueryRepositoryProtocol,
)
from src.modules.tenancy.application.tenant_locale.query.is_tenant_locale_selected.handler import (
    IsTenantLocaleSelectedHandler,
)
from src.modules.tenancy.application.tenant_locale.query.list_system_locales.handler import (
    ListSystemLocalesHandler,
)
from src.modules.tenancy.application.tenant_locale.query.list_tenant_locales.handler import (
    ListTenantLocalesHandler,
)
from src.modules.tenancy.domain.tenant_locale.repository import (
    TenantLocaleRepositoryProtocol,
)
from src.modules.tenancy.infrastructure.tenant_locale.persistence.repository import (
    SqlAlchemyTenantLocaleRepository,
)
from src.modules.tenancy.infrastructure.tenant_locale.persistence.query_repository import (
    SqlAlchemyTenantLocaleQueryRepository,
)


def get_tenant_locale_repository(uow: UoWDep) -> TenantLocaleRepositoryProtocol:
    """Использует общую сессию с привязанной tenant-схемой."""
    return SqlAlchemyTenantLocaleRepository(uow.session)


TenantLocaleRepositoryDep = Annotated[
    TenantLocaleRepositoryProtocol, Depends(get_tenant_locale_repository)
]


def get_tenant_locale_query_repository(
    uow: UoWDep,
) -> TenantLocaleQueryRepositoryProtocol:
    """Связывает чтение с тем же tenant connection."""
    return SqlAlchemyTenantLocaleQueryRepository(uow.session)


TenantLocaleQueryRepositoryDep = Annotated[
    TenantLocaleQueryRepositoryProtocol, Depends(get_tenant_locale_query_repository)
]


def get_add_tenant_locale_handler(
    repository: TenantLocaleRepositoryDep, clock: ClockDep
) -> AddTenantLocaleHandler:
    return AddTenantLocaleHandler(repository, clock)


AddTenantLocaleHandlerDep = Annotated[
    AddTenantLocaleHandler, Depends(get_add_tenant_locale_handler)
]


def get_remove_tenant_locale_handler(
    repository: TenantLocaleRepositoryDep,
) -> RemoveTenantLocaleHandler:
    return RemoveTenantLocaleHandler(repository)


RemoveTenantLocaleHandlerDep = Annotated[
    RemoveTenantLocaleHandler, Depends(get_remove_tenant_locale_handler)
]


def get_list_tenant_locales_handler(
    repository: TenantLocaleQueryRepositoryDep,
) -> ListTenantLocalesHandler:
    return ListTenantLocalesHandler(repository)


ListTenantLocalesHandlerDep = Annotated[
    ListTenantLocalesHandler, Depends(get_list_tenant_locales_handler)
]


def get_is_tenant_locale_selected_handler(
    repository: TenantLocaleQueryRepositoryDep,
) -> IsTenantLocaleSelectedHandler:
    return IsTenantLocaleSelectedHandler(repository)


IsTenantLocaleSelectedHandlerDep = Annotated[
    IsTenantLocaleSelectedHandler, Depends(get_is_tenant_locale_selected_handler)
]


def get_list_system_locales_handler() -> ListSystemLocalesHandler:
    return ListSystemLocalesHandler()


ListSystemLocalesHandlerDep = Annotated[
    ListSystemLocalesHandler, Depends(get_list_system_locales_handler)
]
