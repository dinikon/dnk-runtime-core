from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import uuid6

from src.modules.shared import EntityIdVO
from src.modules.tenancy.domain.tenant.error import (
    InvalidTenantExternalIdError,
    InvalidTenantNameError,
)
from src.modules.tenancy.domain.tenant.value_object import TenantStatus


@dataclass(slots=True)
class Tenant:
    """Доменная сущность tenant и его бизнес-статуса."""

    id: EntityIdVO
    name: str
    external_id: str
    status: TenantStatus
    custom_config: dict[str, object] | None
    created_at: datetime
    updated_at: datetime

    def allows_login(self) -> bool:
        """Показывает, разрешен ли login для tenant."""
        return self.status == TenantStatus.ACTIVE

    def allows_read_business_data(self) -> bool:
        """Показывает, разрешено ли чтение бизнес-данных tenant."""
        return self.status in {TenantStatus.ACTIVE, TenantStatus.FREEZE}

    def allows_write_business_data(self) -> bool:
        """Показывает, разрешена ли запись бизнес-данных tenant."""
        return self.status == TenantStatus.ACTIVE

    @classmethod
    def create(cls, name: str, external_id: str) -> "Tenant":
        """Создает active tenant с нормализованными name и external_id."""
        normalized_name = name.strip()
        normalized_external_id = external_id.strip()
        if not normalized_name:
            raise InvalidTenantNameError()
        if not normalized_external_id:
            raise InvalidTenantExternalIdError()

        now = datetime.now(UTC)
        return cls(
            id=EntityIdVO.from_value(uuid6.uuid7()),
            name=normalized_name,
            external_id=normalized_external_id,
            status=TenantStatus.ACTIVE,
            custom_config=None,
            created_at=now,
            updated_at=now,
        )


__all__ = ["Tenant"]
