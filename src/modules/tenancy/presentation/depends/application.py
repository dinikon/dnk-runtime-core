from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.reference_data.presentation.depends import ValidateCurrencyHandlerDep
from src.modules.tenancy.application.tenant.port.currency_validator import (
    CurrencyValidatorProtocol,
)
from src.modules.tenancy.infrastructure.adapter.currency_validator import (
    ReferenceDataCurrencyValidator,
)
from src.modules.tenancy.application.tenant.port.currency_settings_writer import (
    TenantCurrencySettingsWriterProtocol,
)
from src.modules.tenancy.infrastructure.adapter.tenant_currency_settings import (
    TenantCurrencySettingsPersistenceAdapter,
)

from src.config import dnk_config
from src.modules.tenancy.application.ports.files import TenantStorageProtocol
from src.modules.tenancy.infrastructure.adapter.files import FilesTenantStorageAdapter
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.infrastructure.adapter.schema_bootstrap import (
    AlembicTenantSchemaBootstrapAdapter,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapPort,
)
from src.modules.tenancy.application.tenant.command.create_tenant.handler import (
    CreateTenantHandler,
)
from src.modules.tenancy.application.tenant_domain.use_case.resolve_tenant_by_host import (
    ResolveTenantByHostUseCase,
)
from src.modules.tenancy.application.tenant_domain.use_case.resolve_tenant_request_context_by_host import (
    ResolveTenantRequestContextByHostUseCase,
)
from src.modules.tenancy.presentation.depends.infrastructure import (
    IdentityProvisioningServiceDep,
)
from src.modules.tenancy.presentation.depends.infrastructure import (
    TenantDomainsRepositoryDep,
)
from src.modules.tenancy.presentation.depends.infrastructure import (
    TenantOnboardingServiceDep,
)
from src.modules.tenancy.presentation.depends.infrastructure import TenantsRepositoryDep


def get_tenant_storage(uow: UoWDep) -> TenantStorageProtocol:
    """Собирает файловый адаптер на сессии общего UoW."""
    return FilesTenantStorageAdapter(
        uow.session, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    )


TenantStorageDep = Annotated[TenantStorageProtocol, Depends(get_tenant_storage)]


def get_currency_validator(
    handler: ValidateCurrencyHandlerDep,
) -> CurrencyValidatorProtocol:
    """Соединяет публичную проверку Reference Data с портом Tenancy."""
    return ReferenceDataCurrencyValidator(handler)


CurrencyValidatorDep = Annotated[
    CurrencyValidatorProtocol, Depends(get_currency_validator)
]


def get_currency_settings_writer(uow: UoWDep) -> TenantCurrencySettingsWriterProtocol:
    """Собирает запись настроек после bootstrap в общей транзакции onboarding."""
    return TenantCurrencySettingsPersistenceAdapter(
        uow.session, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    )


TenantCurrencySettingsWriterDep = Annotated[
    TenantCurrencySettingsWriterProtocol, Depends(get_currency_settings_writer)
]


from src.modules.tenancy.application.tenant.port.catalog_provisioning import (
    CatalogProvisioningPort,
)
from src.modules.tenancy.infrastructure.adapter.catalog_provisioning import (
    CatalogProvisioningAdapter,
)
from src.modules.catalog.application.product_type.facade import (
    CatalogProvisioningFacade,
)
from src.modules.catalog.infrastructure.product_type.persistence.repository import (
    SqlAlchemyProductTypeRepository,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator


def get_catalog_provisioning(uow: UoWDep) -> CatalogProvisioningPort:
    """Собирает Catalog и Tenancy adapter на общей сессии создания tenant."""
    return CatalogProvisioningAdapter(
        uow.session,
        TenantSchemaNaming(dnk_config.SCHEMA_PREFIX),
        CatalogProvisioningFacade(
            SqlAlchemyProductTypeRepository(uow.session), UUID7Generator(), UtcClock()
        ),
    )


CatalogProvisioningDep = Annotated[
    CatalogProvisioningPort, Depends(get_catalog_provisioning)
]


def get_create_tenant_handler(
    tenant_onboarding_service: TenantOnboardingServiceDep,
    identity_provisioning_service: IdentityProvisioningServiceDep,
    tenant_schema_bootstrap_context_factory: "TenantSchemaBootstrapContextFactoryDep",
    tenant_schema_bootstrap_port: "TenantSchemaBootstrapPortDep",
    tenant_storage: TenantStorageDep,
    currency_validator: CurrencyValidatorDep,
    currency_settings_writer: TenantCurrencySettingsWriterDep,
    catalog_provisioning: CatalogProvisioningDep,
) -> CreateTenantHandler:
    """Создает use case полного tenant onboarding."""

    return CreateTenantHandler(
        tenant_onboarding_service=tenant_onboarding_service,
        identity_provisioning_service=identity_provisioning_service,
        tenant_schema_bootstrap_context_factory=tenant_schema_bootstrap_context_factory,
        tenant_schema_bootstrap_port=tenant_schema_bootstrap_port,
        tenant_storage=tenant_storage,
        currency_validator=currency_validator,
        currency_settings_writer=currency_settings_writer,
        catalog_provisioning=catalog_provisioning,
    )


CreateTenantHandlerDep = Annotated[
    CreateTenantHandler,
    Depends(get_create_tenant_handler),
]


def get_tenant_schema_bootstrap_context_factory() -> (
    TenantSchemaBootstrapContextFactory
):
    """Создает фабрику bootstrap context из tenant schema конфигурации."""
    return TenantSchemaBootstrapContextFactory(
        schema_prefix=dnk_config.SCHEMA_PREFIX,
    )


TenantSchemaBootstrapContextFactoryDep = Annotated[
    TenantSchemaBootstrapContextFactory,
    Depends(get_tenant_schema_bootstrap_context_factory),
]


def get_tenant_schema_bootstrap_port(
    uow: UoWDep,
) -> TenantSchemaBootstrapPort:
    """Создает порт bootstrap на соединении текущего UoW."""
    return AlembicTenantSchemaBootstrapAdapter(uow.session, TenantMigrator())


TenantSchemaBootstrapPortDep = Annotated[
    TenantSchemaBootstrapPort,
    Depends(get_tenant_schema_bootstrap_port),
]


def get_resolve_tenant_by_host_use_case(
    tenants_repository: TenantsRepositoryDep,
    tenant_domains_repository: TenantDomainsRepositoryDep,
) -> ResolveTenantByHostUseCase:
    """Создает use case публичного resolve tenant по host."""
    return ResolveTenantByHostUseCase(
        tenants_repository=tenants_repository,
        tenant_domains_repository=tenant_domains_repository,
    )


ResolveTenantByHostUseCaseDep = Annotated[
    ResolveTenantByHostUseCase,
    Depends(get_resolve_tenant_by_host_use_case),
]


def get_tenant_request_context_by_host_use_case(
    tenants_repository: TenantsRepositoryDep,
    tenant_domains_repository: TenantDomainsRepositoryDep,
) -> ResolveTenantRequestContextByHostUseCase:
    """Создает use case внутреннего tenant request context по host."""
    return ResolveTenantRequestContextByHostUseCase(
        tenants_repository=tenants_repository,
        tenant_domains_repository=tenant_domains_repository,
    )


TenantRequestContextByHostUseCaseDep = Annotated[
    ResolveTenantRequestContextByHostUseCase,
    Depends(get_tenant_request_context_by_host_use_case),
]


__all__ = [
    "CreateTenantHandlerDep",
    "ResolveTenantByHostUseCaseDep",
    "TenantSchemaBootstrapContextFactoryDep",
    "TenantSchemaBootstrapPortDep",
    "TenantRequestContextByHostUseCaseDep",
    "get_create_tenant_handler",
    "get_resolve_tenant_by_host_use_case",
    "get_tenant_schema_bootstrap_context_factory",
    "get_tenant_schema_bootstrap_port",
    "get_tenant_request_context_by_host_use_case",
]
