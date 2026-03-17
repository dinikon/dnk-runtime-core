from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProvisionedTenantAdmin:
    user_id: UUID
    user_email_id: UUID
    user_status: str


class IdentityProvisioningServiceProtocol(Protocol):
    async def create_tenant_admin(
        self,
        tenant_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
    ) -> ProvisionedTenantAdmin: ...


__all__ = [
    "IdentityProvisioningServiceProtocol",
    "ProvisionedTenantAdmin",
]
