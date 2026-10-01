from __future__ import annotations

from typing import Protocol
from uuid import UUID


class AuthorizationServiceProtocol(Protocol):
    """Порт проверки прав principal на действие с ресурсом."""

    async def can(
        self,
        *,
        user_id: UUID | None,
        tenant_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None = None,
    ) -> bool:
        """Возвращает True, если действие разрешено."""
        ...
