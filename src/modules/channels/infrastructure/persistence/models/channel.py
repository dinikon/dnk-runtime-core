from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ChannelModel(TenantBase):
    """Описывает tenant-хранение channels без бизнес-переходов."""

    __tablename__ = "channels"
    __table_args__ = (sa.CheckConstraint("revision > 0", name="ck_channels_revision"),)
    id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    platform_kind: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.false()
    )
    is_archived: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.false()
    )
    revision: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False)
