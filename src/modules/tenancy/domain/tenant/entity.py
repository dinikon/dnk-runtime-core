from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import uuid6

from src.modules.tenancy.domain.tenant.error import InvalidTenantExternalIdError
from src.modules.tenancy.domain.tenant.error import InvalidTenantNameError
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.domain.tenant.value_object.tenant_status import TenantStatus


@dataclass(slots=True)
class Tenant:
    """Доменная сущность tenant и его бизнес-статуса."""

    id: TenantIdVO
    name: str
    external_id: str
    status: TenantStatus
    custom_config: dict[str, object] | None
    created_at: datetime
    updated_at: datetime

    def activate(self, *, storage_ready: bool) -> None:
        """Активирует tenant только после подтверждения готовности хранилища."""
        if not storage_ready or self.status not in {
            TenantStatus.PROVISIONING,
            TenantStatus.ACTIVE,
        }:
            from src.modules.tenancy.domain.tenant.error import (
                TenantCannotActivateError,
            )

            raise TenantCannotActivateError(
                "Tenant cannot be activated before storage is ready."
            )
        self.status = TenantStatus.ACTIVE
        self.updated_at = datetime.now(UTC)

    @classmethod
    def restore(
        cls,
        *,
        tenant_id: TenantIdVO,
        name: str,
        external_id: str,
        status: TenantStatus,
        custom_config: dict[str, object] | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> "Tenant":
        """Восстанавливает tenant через явную фабрику с проверкой обязательных значений."""
        if not name.strip():
            raise InvalidTenantNameError()
        if not external_id.strip():
            raise InvalidTenantExternalIdError()
        return cls(
            tenant_id, name, external_id, status, custom_config, created_at, updated_at
        )

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
    def create(
        cls,
        name: str,
        external_id: str,
        *,
        tenant_id: TenantIdVO | None = None,
        status: TenantStatus = TenantStatus.ACTIVE,
    ) -> "Tenant":
        """Создает active tenant с нормализованными name и external_id."""
        normalized_name = name.strip()
        normalized_external_id = external_id.strip()
        if not normalized_name:
            raise InvalidTenantNameError()
        if not normalized_external_id:
            raise InvalidTenantExternalIdError()

        now = datetime.now(UTC)
        return cls(
            id=tenant_id or TenantIdVO.from_value(uuid6.uuid7()),
            name=normalized_name,
            external_id=normalized_external_id,
            status=status,
            custom_config=None,
            created_at=now,
            updated_at=now,
        )


__all__ = ["Tenant"]
