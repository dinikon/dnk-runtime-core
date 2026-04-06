from __future__ import annotations

from src.config import dnk_config
from src.modules.schema_registry.application.command.create_schema_command import (
    CreateSchemaCommand,
)
from src.modules.schema_registry.application.use_case.create_schema_use_case import (
    CreateSchemaUseCase,
)
from src.modules.tenancy.application.commands import CreateTenantCommand
from src.modules.tenancy.application.dto import CreateTenantResultDTO
from src.modules.tenancy.application.ports.identity import (
    IdentityProvisioningServiceProtocol,
)
from src.modules.tenancy.domain.services import TenantOnboardingService


class CreateTenantUseCase:

    def __init__(
        self,
        tenant_onboarding_service: TenantOnboardingService,
        identity_provisioning_service: IdentityProvisioningServiceProtocol,
        create_schema_use_case: CreateSchemaUseCase,
    ):
        self._tenant_onboarding_service = tenant_onboarding_service
        self._identity_provisioning_service = identity_provisioning_service
        self._create_schema_use_case = create_schema_use_case

    async def execute(self, command: CreateTenantCommand) -> CreateTenantResultDTO:
        onboarding = (
            await self._tenant_onboarding_service.create_tenant_with_primary_domain(
                tenant_name=command.tenant_name,
                external_id=command.external_id,
                tenant_domain_host=command.tenant_domain_host,
            )
        )

        user = await self._identity_provisioning_service.create_tenant_admin(
            tenant_id=onboarding.tenant.id,
            first_name=command.user_first_name,
            last_name=command.user_last_name,
            email=command.user_email,
        )
        await self._create_schema_use_case.execute(
            CreateSchemaCommand(
                tenant_id=onboarding.tenant.id,
                schema_name=f"{dnk_config.SCHEMA_PREFIX}{onboarding.tenant.id.hex}",
                seed_path=dnk_config.DEFAULT_SEED_MODULE,
            )
        )

        return CreateTenantResultDTO(
            tenant_id=onboarding.tenant.id,
            user_id=user.user_id,
            user_email_id=user.user_email_id,
            tenant_domain_id=onboarding.tenant_domain.id,
            tenant_status=onboarding.tenant.status.value,
            user_status=user.user_status,
            tenant_domain_host=onboarding.tenant_domain.host,
        )


__all__ = ["CreateTenantUseCase"]
