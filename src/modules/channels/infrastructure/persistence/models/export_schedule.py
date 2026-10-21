from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ExportScheduleModel(TenantBase):
    """Хранит ежедневную policy независимо от generation и credentials подключения."""

    __tablename__ = "channel_export_schedules"
    __table_args__ = (
        sa.CheckConstraint(
            "hour BETWEEN 0 AND 23 AND minute BETWEEN 0 AND 59 AND revision > 0",
            name="ck_export_schedule_time",
        ),
        sa.CheckConstraint(
            "enabled = (next_at IS NOT NULL)", name="ck_export_schedule_next"
        ),
    )
    channel_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channels.id"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)
    hour: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    minute: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    timezone: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    revision: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    next_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
