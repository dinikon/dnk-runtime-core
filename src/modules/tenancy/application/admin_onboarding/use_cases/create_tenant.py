from __future__ import annotations

from modules.shared.db.uow import UnitOfWorkProtocol
from src.modules.tenancy.application.admin_onboarding.dto import (
    CreateTenantCommandDTO,
    CreateTenantResultDTO,
)
from src.modules.tenancy.application.admin_onboarding.ports.identity import (
    IdentityProvisioningServiceProtocol,
)
from src.modules.tenancy.application.admin_onboarding.ports.storage import (
    TenantSchemaProvisionerProtocol,
)
from src.modules.tenancy.application.admin_onboarding.services.tenant_domain_service import (
    TenantDomainServiceProtocol,
)
from src.modules.tenancy.application.admin_onboarding.services.tenant_schema_name_service import (
    TenantSchemaNameServiceProtocol,
)
from src.modules.tenancy.application.admin_onboarding.services.tenant_service import (
    TenantServiceProtocol,
)


class CreateTenantUseCase:
    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        tenant_service: TenantServiceProtocol,
        identity_provisioning_service: IdentityProvisioningServiceProtocol,
        tenant_domain_service: TenantDomainServiceProtocol,
        tenant_schema_name_service: TenantSchemaNameServiceProtocol,
        tenant_schema_provisioner: TenantSchemaProvisionerProtocol,
    ):
        self._uow = uow
        self._tenant_service = tenant_service
        self._identity_provisioning_service = identity_provisioning_service
        self._tenant_domain_service = tenant_domain_service
        self._tenant_schema_name_service = tenant_schema_name_service
        self._tenant_schema_provisioner = tenant_schema_provisioner

    async def execute(self, dto: CreateTenantCommandDTO) -> CreateTenantResultDTO:
        try:
            tenant = await self._tenant_service.create_tenant(
                dto.tenant_name,
                dto.external_id,
            )
            tenant_domain = (
                await self._tenant_domain_service.create_primary_console_domain(
                    tenant_id=tenant.id,
                    host=dto.tenant_domain_host,
                )
            )
            tenant_schema = self._tenant_schema_name_service.build_schema_name(
                tenant.id
            )
            await self._tenant_schema_provisioner.create_schema(tenant_schema)
            user = await self._identity_provisioning_service.create_tenant_admin(
                tenant_id=tenant.id,
                first_name=dto.user_first_name,
                last_name=dto.user_last_name,
                email=dto.user_email,
            )
            await self._uow.commit()
        except Exception:
            await self._uow.rollback()
            raise

        return CreateTenantResultDTO(
            tenant_id=tenant.id,
            user_id=user.user_id,
            user_email_id=user.user_email_id,
            tenant_domain_id=tenant_domain.id,
            tenant_status=tenant.status,
            user_status=user.user_status,
            tenant_domain_host=tenant_domain.host,
        )
