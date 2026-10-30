from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.channels.domain.types import JsonObject
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import (
    TenantBase,
    TENANT_SCHEMA_ALIAS,
)


class StockSyncModel(TenantBase):
    """Хранилище текущего состояния одного физического остатка, без бизнес-CHECK."""

    __tablename__ = "channel_stock_sync_states"
    __table_args__ = (sa.Index("ix_channel_stock_binding", "binding_group_id"),)
    publication_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            f"{TENANT_SCHEMA_ALIAS}.channel_external_publications.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    connection_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            f"{TENANT_SCHEMA_ALIAS}.channel_connections.id", ondelete="CASCADE"
        ),
        nullable=False,
    )
    operation_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    direction: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    config_revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    policy_revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    binding_group_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            f"{TENANT_SCHEMA_ALIAS}.channel_catalog_binding_groups.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    binding_revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    observed: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    desired_quantity: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
