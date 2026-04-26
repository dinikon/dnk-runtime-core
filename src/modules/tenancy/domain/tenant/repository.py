from __future__ import annotations

from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.tenancy.domain.tenant.entity import Tenant


class TenantRepositoryProtocol(Protocol):
    """Порт хранения tenant entities."""

    async def add(self, tenant: Tenant) -> None:
        """Добавляет tenant в хранилище."""
        ...

    async def get_by_id(self, tenant_id: EntityIdVO) -> Tenant | None:
        """Возвращает tenant по id или None."""
        ...

    async def get_by_name(self, name: str) -> Tenant | None:
        """Возвращает tenant по имени или None."""
        ...

    async def exists_by_external_id(self, external_id: str) -> bool:
        """Проверяет наличие tenant с указанным external_id."""
        ...

    async def exists_by_name(self, name: str) -> bool:
        """Проверяет наличие tenant с указанным именем."""
        ...


__all__ = ["TenantRepositoryProtocol"]
