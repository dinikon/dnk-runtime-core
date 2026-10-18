from datetime import datetime
from decimal import Decimal
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


class ExternalPublicationModel(TenantBase):
    """Описывает tenant-хранение channel_external_publications без бизнес-переходов."""

    __tablename__ = "channel_external_publications"
    __table_args__ = (
        sa.UniqueConstraint(
            "connection_id",
            "resource_type",
            "external_id",
            name="uq_channel_external_publications_identity",
        ),
        sa.Index("ix_channel_publications_list", "connection_id", "id"),
        sa.Index("ix_channel_publications_sku", "connection_id", "external_sku"),
        sa.Index("ix_channel_publications_stock", "connection_id", "stock_status"),
        sa.CheckConstraint(
            "observed_revision > 0 AND core_version = 1",
            name="ck_channel_publications_revision",
        ),
    )
    id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False, primary_key=True)
    connection_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("tenant.channel_connections.id"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    external_id: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    external_sku: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(sa.Numeric(30, 12), nullable=True)
    sale_price: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(30, 12), nullable=True
    )
    currency: Mapped[str | None] = mapped_column(sa.String(3), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(sa.Numeric(30, 12), nullable=True)
    stock_status: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    title: Mapped[str | None] = mapped_column(sa.String(2000), nullable=True)
    title_locale: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    main_image_url: Mapped[str | None] = mapped_column(sa.String(4096), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    warnings: Mapped[list[str]] = mapped_column(JSONB(), nullable=False)
    core_version: Mapped[int] = mapped_column(
        sa.Integer(), nullable=False, server_default=sa.text("1")
    )
    extension_version: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    extensions: Mapped[dict[str, JsonValue]] = mapped_column(JSONB(), nullable=False)
    fingerprint: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    observed_revision: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    last_import_run_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("tenant.channel_sync_runs.id"), nullable=False
    )
