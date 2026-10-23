from typing import Protocol
from uuid import UUID


class TenantPublicHostsFacade(Protocol):
    """Публичный read-контракт зарегистрированных активных доменов tenant."""

    async def primary_host(self, tenant_id: UUID) -> str | None:
        """Возвращает основной Console host с резервным API host без HTTP-заголовков."""
        ...

    async def owns_host(self, tenant_id: UUID, host: str) -> bool:
        """Проверяет принадлежность активного host указанному tenant."""
        ...
