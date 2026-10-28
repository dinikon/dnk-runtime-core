from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class PositionHistoryModel(TenantBase):
    """Append-only история CRM без FK к удаляемым стадиям."""

    __tablename__ = "crm_position_history"
    __table_args__ = (
        sa.CheckConstraint(
            "model_key IN ('crm.lead','crm.deal')", name="ck_position_history_model"
        ),
        sa.CheckConstraint(
            "reason IN ('created','manual_move','funnel_changed','stage_deleted')",
            name="ck_position_history_reason",
        ),
        sa.CheckConstraint(
            "current_revision > 0 AND (previous_revision IS NULL OR current_revision = previous_revision + 1)",
            name="ck_position_history_revision",
        ),
        sa.UniqueConstraint(
            "model_key",
            "record_id",
            "current_revision",
            name="uq_position_history_revision",
        ),
        sa.Index(
            "ix_position_history_card_time", "model_key", "record_id", "occurred_at"
        ),
        sa.Index("ix_position_history_time", "occurred_at"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    model_key: Mapped[str] = mapped_column(sa.String(32))
    record_id: Mapped[UUID] = mapped_column(StringUUID)
    previous: Mapped[dict | None] = mapped_column(sa.JSON(none_as_null=True))
    current: Mapped[dict] = mapped_column(sa.JSON)
    previous_revision: Mapped[int | None] = mapped_column(sa.Integer)
    current_revision: Mapped[int] = mapped_column(sa.Integer)
    reason: Mapped[str] = mapped_column(sa.String(32))
    actor_id: Mapped[UUID] = mapped_column(StringUUID)
    occurred_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
