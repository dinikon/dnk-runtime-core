from __future__ import annotations

from src.modules.shared.presentation.http.host import normalize_host
from src.modules.tenancy.application.tenant_domain.dto import TenantRequestContextDTO
from src.modules.tenancy.application.tenant_domain.query import (
    ResolveTenantRequestContextByHostQuery,
)
from src.modules.tenancy.domain.tenant import TenantRepositoryProtocol
from src.modules.tenancy.domain.tenant_domain import (
    TenantDomainRepositoryProtocol,
    TenantDomainStatus,
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)


class ResolveTenantRequestContextByHostUseCase:
    """Use case получения внутреннего tenant request context по host."""

    def __init__(
        self,
        tenants_repository: TenantRepositoryProtocol,
        tenant_domains_repository: TenantDomainRepositoryProtocol,
    ) -> None:
        """Инициализирует use case репозиториями tenants и tenant domains."""
        self._tenants_repository = tenants_repository
        self._tenant_domains_repository = tenant_domains_repository

    async def execute(
        self,
        query: ResolveTenantRequestContextByHostQuery,
    ) -> TenantRequestContextDTO:
        """Возвращает request context или поднимает not-found/login unavailable ошибки."""
        normalized_host = normalize_host(query.host)
        if not normalized_host:
            raise TenantHostNotFoundError(normalized_host)

        tenant_domain = await self._tenant_domains_repository.get_by_host(
            normalized_host
        )
        if tenant_domain is None:
            raise TenantHostNotFoundError(normalized_host)

        tenant = await self._tenants_repository.get_by_id(tenant_domain.tenant_id)
        if tenant is None:
            raise TenantHostNotFoundError(normalized_host)
        if (
            tenant_domain.status != TenantDomainStatus.ACTIVE
            or not tenant.allows_login()
        ):
            raise TenantLoginUnavailableError(normalized_host)

        api_host = await self._tenant_domains_repository.get_api_host_by_tenant_id(
            tenant.id
        )
        if api_host is None:
            api_host = tenant_domain.host

        return TenantRequestContextDTO(
            tenant_id=tenant.id.uuid,
            tenant_domain_id=tenant_domain.id.uuid,
            host=tenant_domain.host,
            tenant_status=tenant.status.value,
            domain_status=tenant_domain.status.value,
            api_host=api_host,
        )


__all__ = ["ResolveTenantRequestContextByHostUseCase"]
