from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import uuid6

from src.modules.shared.domain.errors import DomainError
from src.modules.tenancy.domain.tenant.value_objects.tenant_status import TenantStatus


@dataclass(slots=True)
class Tenant:
    id: UUID
    name: str
    external_id: str
    status: TenantStatus
    custom_config: dict[str, object] | None
    created_at: datetime
    updated_at: datetime

    def allows_login(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    def allows_read_business_data(self) -> bool:
        return self.status in {TenantStatus.ACTIVE, TenantStatus.FREEZE}

    def allows_write_business_data(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    @classmethod
    def create(cls, name: str, external_id: str) -> "Tenant":
        normalized_name = name.strip()
        normalized_external_id = external_id.strip()
        if not normalized_name:
            raise DomainError("Tenant name must not be empty.")
        if not normalized_external_id:
            raise DomainError("Tenant external_id must not be empty.")

        now = datetime.now(UTC)
        return cls(
            id=uuid6.uuid7(),
            name=normalized_name,
            external_id=normalized_external_id,
            status=TenantStatus.ACTIVE,
            custom_config=None,
            created_at=now,
            updated_at=now,
        )
