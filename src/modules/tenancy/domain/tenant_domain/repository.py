from __future__ import annotations

from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.tenancy.domain.tenant_domain.entity import TenantDomain
from src.modules.tenancy.domain.tenant_domain.value_object import TenantDomainIdVO

class TenantDomainRepositoryProtocol(Protocol):
    """Порт хранения tenant domain entities."""

    async def add(self, domain: TenantDomain) -> None:
        """Добавляет tenant domain в хранилище."""
        ...

    async def get_by_id(self, domain_id: TenantDomainIdVO) -> TenantDomain | None:
        """Возвращает tenant domain по id или None."""
        ...

    async def get_by_host(self, host: str) -> TenantDomain | None:
        """Возвращает активный tenant domain по host или None."""
        ...

    async def get_api_host_by_tenant_id(self, tenant_id: EntityIdVO) -> str | None:
        """Возвращает API host tenant или None."""
        ...

    async def exists_by_host(self, host: str) -> bool:
        """Проверяет наличие не удаленного tenant domain по host."""
        ...


__all__ = ["TenantDomainRepositoryProtocol"]
