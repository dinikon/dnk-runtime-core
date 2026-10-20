from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


class PublicationImportModel(TenantBase):
    """Хранит lifecycle одной подготовки и её ограниченный нормализованный снимок."""

    __tablename__ = "channel_publication_import_preparations"
    __table_args__ = (
        sa.CheckConstraint(
            "revision > 0 AND sequence >= 0 AND observed_revision > 0 AND connection_generation >= 0",
            name="ck_channel_import_revision",
        ),
        sa.CheckConstraint(
            "status IN ('queued','reading','images','ready','error','consumed','expired','cancelled')",
            name="ck_channel_import_status",
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name="ck_channel_import_expiration"
        ),
        sa.Index("ix_channel_import_expiration", "expires_at", "id"),
        sa.Index("ix_channel_import_publication", "publication_id", "actor_id"),
    )
    id: Mapped[UUID] = mapped_column(sa.UUID(), primary_key=True)
    publication_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_external_publications.id"), nullable=False
    )
    actor_id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False)
    connection_generation: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    observed_revision: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    revision: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    sequence: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    snapshot: Mapped[dict[str, JsonValue] | None] = mapped_column(
        JSONB(), nullable=True
    )
    media: Mapped[dict[str, JsonValue]] = mapped_column(JSONB(), nullable=False)
    error_code: Mapped[str | None] = mapped_column(sa.String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    used_image_ids: Mapped[list[str]] = mapped_column(JSONB(), nullable=False)
