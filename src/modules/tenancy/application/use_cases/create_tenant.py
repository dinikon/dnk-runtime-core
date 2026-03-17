from __future__ import annotations

from src.modules.shared.db.uow import UnitOfWorkProtocol
from src.modules.shared.http.host import normalize_host
from src.modules.tenancy.application.commands import CreateTenantCommand
from src.modules.tenancy.application.dto import CreateTenantResultDTO
from src.modules.tenancy.application.ports.identity import (
    IdentityProvisioningServiceProtocol,
)
from src.modules.tenancy.domain.entities import Tenant, TenantDomain
from src.modules.tenancy.domain.errors import (
    InvalidTenantDomainHostError,
    TenantDomainHostAlreadyExistsError,
    TenantExternalIdAlreadyExistsError,
    TenantNameAlreadyExistsError,
)
from src.modules.tenancy.domain.repositories import (
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
)


class CreateTenantUseCase:
    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        tenants_repository: TenantRepositoryProtocol,
        tenant_domains_repository: TenantDomainRepositoryProtocol,
        identity_provisioning_service: IdentityProvisioningServiceProtocol,
    ):
        self._uow = uow
        self._tenants_repository = tenants_repository
        self._tenant_domains_repository = tenant_domains_repository
        self._identity_provisioning_service = identity_provisioning_service

    async def execute(self, command: CreateTenantCommand) -> CreateTenantResultDTO:
        if getattr(self._uow, "session", None) is None:
            async with self._uow:
                return await self._create_within_transaction(command)
        return await self._create_within_transaction(command)

    async def _create_within_transaction(
        self,
        command: CreateTenantCommand,
    ) -> CreateTenantResultDTO:
        normalized_name = command.tenant_name.strip()
        normalized_external_id = command.external_id.strip()
        normalized_host = normalize_host(command.tenant_domain_host)
        if not normalized_host:
            raise InvalidTenantDomainHostError()

        if await self._tenants_repository.exists_by_name(normalized_name):
            raise TenantNameAlreadyExistsError(normalized_name)
        if await self._tenants_repository.exists_by_external_id(normalized_external_id):
            raise TenantExternalIdAlreadyExistsError(normalized_external_id)
        if await self._tenant_domains_repository.exists_by_host(normalized_host):
            raise TenantDomainHostAlreadyExistsError(normalized_host)

        tenant = Tenant.create(
            name=normalized_name,
            external_id=normalized_external_id,
        )
        await self._tenants_repository.add(tenant)

        tenant_domain = TenantDomain.create_primary_console_domain(
            tenant_id=tenant.id,
            host=normalized_host,
        )
        await self._tenant_domains_repository.add(tenant_domain)

        user = await self._identity_provisioning_service.create_tenant_admin(
            tenant_id=tenant.id,
            first_name=command.user_first_name,
            last_name=command.user_last_name,
            email=command.user_email,
        )
        await self._uow.commit()

        return CreateTenantResultDTO(
            tenant_id=tenant.id,
            user_id=user.user_id,
            user_email_id=user.user_email_id,
            tenant_domain_id=tenant_domain.id,
            tenant_status=tenant.status.value,
            user_status=user.user_status,
            tenant_domain_host=tenant_domain.host,
        )


__all__ = ["CreateTenantUseCase"]
