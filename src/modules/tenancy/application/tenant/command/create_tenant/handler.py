from __future__ import annotations

from src.modules.tenancy.application.tenant.port.catalog_provisioning import (
    CatalogProvisioningPort,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO

from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.tenancy.application.tenant.port.currency_validator import (
    CurrencyValidatorProtocol,
)
from src.modules.tenancy.application.tenant.port.currency_settings_writer import (
    TenantCurrencySettingsWriterProtocol,
)
from src.modules.tenancy.domain.tenant_currency_settings.aggregate import (
    TenantCurrencySettings,
)

from src.modules.tenancy.application.ports.files import TenantStorageProtocol

from src.modules.tenancy.application.ports.identity import (
    IdentityProvisioningServiceProtocol,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapPort,
)
from src.modules.tenancy.application.tenant.command.create_tenant.command import (
    CreateTenantCommand,
)
from src.modules.tenancy.application.tenant.command.create_tenant.dto import (
    CreateTenantResultDTO,
)
from src.modules.tenancy.application.tenant.onboarding import TenantOnboardingService
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO


class CreateTenantHandler:
    """Подготовка tenant, администратора, схемы и регистрации приватного хранилища."""

    def __init__(
        self,
        tenant_onboarding_service: TenantOnboardingService,
        identity_provisioning_service: IdentityProvisioningServiceProtocol,
        tenant_schema_bootstrap_context_factory: TenantSchemaBootstrapContextFactory,
        tenant_schema_bootstrap_port: TenantSchemaBootstrapPort,
        tenant_storage: TenantStorageProtocol,
        currency_validator: CurrencyValidatorProtocol,
        currency_settings_writer: TenantCurrencySettingsWriterProtocol,
        catalog_provisioning: CatalogProvisioningPort,
    ) -> None:
        """Инициализирует orchestration зависимости tenant onboarding."""
        self._catalog_provisioning = catalog_provisioning
        self._tenant_storage = tenant_storage
        self._currency_validator = currency_validator
        self._currency_settings_writer = currency_settings_writer
        self._tenant_onboarding_service = tenant_onboarding_service
        self._identity_provisioning_service = identity_provisioning_service
        self._tenant_schema_bootstrap_context_factory = (
            tenant_schema_bootstrap_context_factory
        )
        self._tenant_schema_bootstrap_port = tenant_schema_bootstrap_port

    async def execute(self, command: CreateTenantCommand) -> CreateTenantResultDTO:
        """Подготавливает tenant, оставляя активацию следующему durable этапу.

        Сначала создается tenant и primary domain, затем bootstrap tenant-схемы
        через внешний порт, регистрирует файловый бакет, затем tenant admin и Default Catalog.
        Внешняя сборка фиксирует этап до обращения к MinIO.
        """
        base_currency = CurrencyVO.from_value(command.base_currency)
        await self._currency_validator.ensure_supported(base_currency)
        onboarding = (
            await self._tenant_onboarding_service.create_tenant_with_primary_domain(
                tenant_name=command.tenant_name,
                external_id=command.external_id,
                tenant_domain_host=command.tenant_domain_host,
                **(
                    {
                        "reserved_tenant_id": TenantIdVO.from_value(
                            command.reserved_tenant_id
                        )
                    }
                    if command.reserved_tenant_id
                    else {}
                ),
            )
        )

        await self._tenant_schema_bootstrap_port.bootstrap(
            context=self._tenant_schema_bootstrap_context_factory.build(
                tenant_id=onboarding.tenant.id,
            )
        )
        await self._currency_settings_writer.initialize(
            onboarding.tenant.id,
            TenantCurrencySettings.create(base_currency=base_currency),
        )
        await self._tenant_storage.register(onboarding.tenant.id.uuid)
        user = await self._identity_provisioning_service.create_tenant_admin(
            tenant_id=onboarding.tenant.id,
            first_name=command.user_first_name,
            last_name=command.user_last_name,
            email=command.user_email,
        )

        await self._catalog_provisioning.initialize_defaults(
            onboarding.tenant.id, EntityIdVO(user.user_id)
        )

        return CreateTenantResultDTO(
            tenant_id=onboarding.tenant.id.uuid,
            user_id=user.user_id,
            user_email_id=user.user_email_id,
            tenant_domain_id=onboarding.tenant_domain.id.uuid,
            tenant_status=onboarding.tenant.status.value,
            user_status=user.user_status,
            tenant_domain_host=onboarding.tenant_domain.host,
            base_currency=base_currency.value,
        )
