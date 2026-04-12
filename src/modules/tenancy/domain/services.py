from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared.http.host import normalize_host
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


@dataclass(frozen=True, slots=True)
class TenantOnboardingDraft:
    """Промежуточный результат создания tenant и primary domain."""

    tenant: Tenant
    tenant_domain: TenantDomain


class TenantOnboardingService:
    """Доменный сервис onboarding tenant и его primary domain."""

    def __init__(
        self,
        tenants_repository: TenantRepositoryProtocol,
        tenant_domains_repository: TenantDomainRepositoryProtocol,
    ) -> None:
        """Инициализирует сервис репозиториями tenants и domains."""
        self._tenants_repository = tenants_repository
        self._tenant_domains_repository = tenant_domains_repository

    async def create_tenant_with_primary_domain(
        self,
        *,
        tenant_name: str,
        external_id: str,
        tenant_domain_host: str,
    ) -> TenantOnboardingDraft:
        """Создает tenant с primary console domain после проверок уникальности."""
        normalized_name = tenant_name.strip()
        normalized_external_id = external_id.strip()
        normalized_host = normalize_host(tenant_domain_host)
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
        return TenantOnboardingDraft(
            tenant=tenant,
            tenant_domain=tenant_domain,
        )


__all__ = [
    "TenantOnboardingDraft",
    "TenantOnboardingService",
]
