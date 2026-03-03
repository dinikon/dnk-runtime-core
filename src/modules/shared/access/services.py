from __future__ import annotations

from uuid import UUID

from src.modules.shared.access.protocols import AuthorizationServiceProtocol


class AllowAllAuthorizationService:
    async def can(
        self,
        *,
        user_id: UUID | None,
        tenant_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None = None,
    ) -> bool:
        return True
