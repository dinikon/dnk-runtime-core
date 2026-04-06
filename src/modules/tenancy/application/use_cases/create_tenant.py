from __future__ import annotations

from src.modules.tenancy.application.commands import CreateTenantCommand
from src.modules.tenancy.application.dto import CreateTenantResultDTO
from src.modules.tenancy.application.ports.identity import (
    IdentityProvisioningServiceProtocol,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
    TenantSchemaBootstrapPort,
)
from src.modules.tenancy.domain.services import TenantOnboardingService


class CreateTenantUseCase:

    def __init__(
        self,
        tenant_onboarding_service: TenantOnboardingService,
        identity_provisioning_service: IdentityProvisioningServiceProtocol,
        tenant_schema_bootstrap_context_factory: TenantSchemaBootstrapContextFactory,
        tenant_schema_bootstrap_port: TenantSchemaBootstrapPort,
    ):
        self._tenant_onboarding_service = tenant_onboarding_service
        self._identity_provisioning_service = identity_provisioning_service
        self._tenant_schema_bootstrap_context_factory = (
            tenant_schema_bootstrap_context_factory
        )
        self._tenant_schema_bootstrap_port = tenant_schema_bootstrap_port

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
        await self._tenant_schema_bootstrap_port.bootstrap(
            context=self._tenant_schema_bootstrap_context_factory.build(
                tenant_id=onboarding.tenant.id,
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
