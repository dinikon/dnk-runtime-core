from __future__ import annotations

from src.application.admin_tenants.dto import (
    CreateTenantCommandDTO,
    CreateTenantResultDTO,
)
from src.application.admin_tenants.services.tenant_domain_service import (
    TenantDomainServiceProtocol,
)
from src.application.admin_tenants.services.tenant_service import TenantServiceProtocol
from src.application.admin_tenants.services.user_service import UserServiceProtocol
from src.common.uow import UnitOfWorkProtocol


class CreateTenantUseCase:
    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        tenant_service: TenantServiceProtocol,
        user_service: UserServiceProtocol,
        tenant_domain_service: TenantDomainServiceProtocol,
    ):
        self._uow = uow
        self._tenant_service = tenant_service
        self._user_service = user_service
        self._tenant_domain_service = tenant_domain_service

    async def execute(self, dto: CreateTenantCommandDTO) -> CreateTenantResultDTO:
        try:
            tenant = await self._tenant_service.create_tenant(dto.tenant_name)
            user = await self._user_service.create_tenant_admin(
                tenant_id=tenant.id,
                first_name=dto.user_first_name,
                last_name=dto.user_last_name,
                email=dto.user_email,
            )
            tenant_domain = await self._tenant_domain_service.create_primary_domain(
                tenant_id=tenant.id,
                host=dto.tenant_domain_host,
            )
            await self._uow.commit()
        except Exception:
            await self._uow.rollback()
            raise

        primary_email = next(
            email for email in user.emails if email.is_primary and not email.is_deleted
        )
        return CreateTenantResultDTO(
            tenant_id=tenant.id,
            user_id=user.id,
            user_email_id=primary_email.id,
            tenant_domain_id=tenant_domain.id,
            tenant_status=tenant.status,
            user_status=user.status,
            tenant_domain_host=tenant_domain.host,
        )
