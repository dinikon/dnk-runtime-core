from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared.presentation.http.host import normalize_host
from src.modules.tenancy.domain.tenant import (
    Tenant,
    TenantExternalIdAlreadyExistsError,
    TenantNameAlreadyExistsError,
    TenantRepositoryProtocol,
    TenantStatus,
)
from src.modules.tenancy.domain.tenant.value_object import TenantIdVO
from src.modules.tenancy.domain.tenant_domain import (
    InvalidTenantDomainHostError,
    TenantDomain,
    TenantDomainHostAlreadyExistsError,
    TenantDomainRepositoryProtocol,
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
        reserved_tenant_id: TenantIdVO | None = None,
    ) -> TenantOnboardingDraft:
        """Создает tenant с primary console domain после проверок уникальности."""
        normalized_name = tenant_name.strip()
        normalized_external_id = external_id.strip()
        normalized_host = normalize_host(tenant_domain_host)
        if not normalized_host:
            raise InvalidTenantDomainHostError()

        if await self._tenants_repository.exists_by_external_id(normalized_external_id):
            raise TenantExternalIdAlreadyExistsError(normalized_external_id)
        if await self._tenant_domains_repository.exists_by_host(normalized_host):
            raise TenantDomainHostAlreadyExistsError(normalized_host)

        tenant = Tenant.create(
            name=normalized_name,
            external_id=normalized_external_id,
            tenant_id=reserved_tenant_id,
            status=(
                TenantStatus.PROVISIONING if reserved_tenant_id else TenantStatus.ACTIVE
            ),
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
