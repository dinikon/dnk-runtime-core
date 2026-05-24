from __future__ import annotations

from uuid import UUID

from src.modules.shared.application.access import AuthorizationServiceProtocol


class AllowAllAuthorizationService(AuthorizationServiceProtocol):
    """Authorization service-заглушка, разрешающая все действия."""

    async def can(
        self,
        *,
        user_id: UUID | None,
        tenant_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None = None,
    ) -> bool:
        """Всегда возвращает True для development/default сценариев."""
        return True
