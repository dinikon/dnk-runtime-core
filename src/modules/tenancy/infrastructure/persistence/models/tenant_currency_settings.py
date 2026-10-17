from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class TenantCurrencySettingsModel(TenantBase):
    """Отдельная tenant-модель для базовой валюты и будущих валютных настроек."""

    __tablename__ = "tenant_currency_settings"
    __table_args__ = (
        sa.CheckConstraint("id = 1", name="ck_tenant_currency_settings_singleton"),
    )

    id: Mapped[int] = mapped_column(sa.SmallInteger, primary_key=True)
    base_currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
