from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantRequestContext:
    """Контекст tenant/domain, разрешенный по request host."""

    tenant_id: UUID
    tenant_domain_id: UUID
    host: str
    tenant_status: str
    domain_status: str
    api_host: str | None


class TenantContextReaderPort(Protocol):
    """Порт чтения tenant request context по host."""

    async def get_by_host(self, host: str) -> TenantRequestContext:
        """Возвращает tenant context или поднимает IdentityTenantNotFoundError или IdentityTenantUnavailableError."""
        ...


class IdentityTenantNotFoundError(Exception):
    """Tenant для host не найден."""


class IdentityTenantUnavailableError(Exception):
    """Tenant не допускает вход."""
