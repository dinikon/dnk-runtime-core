from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase

TENANT_CURRENCY_SETTINGS_ID = UUID("00000000-0000-0000-0000-000000000001")


class TenantCurrencySettingsModel(TenantBase):
    """Отдельная tenant-модель для базовой валюты и будущих валютных настроек."""

    __tablename__ = "tenant_currency_settings"
    __table_args__ = (
        sa.CheckConstraint(
            f"id = '{TENANT_CURRENCY_SETTINGS_ID}'",
            name="ck_tenant_currency_settings_singleton",
        ),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    base_currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
