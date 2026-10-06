from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID


class ExternalPublicationModel(TenantBase):
    """Хранит исходный JSON и нормализованный Read документ отдельной публикации."""

    __tablename__ = "channel_publications"
    __table_args__ = (
        sa.UniqueConstraint(
            "channel_id",
            "connection_revision",
            "resource_type",
            "external_id",
            name="uq_channel_publication_identity",
        ),
        sa.Index(
            "ix_channel_publication_list",
            "channel_id",
            "connection_revision",
            "resource_type",
            "id",
        ),
        sa.Index(
            "ix_channel_publication_parent",
            "channel_id",
            "connection_revision",
            "parent_external_id",
        ),
        sa.CheckConstraint(
            "connection_revision > 0 AND revision > 0", name="ck_publication_revision"
        ),
        sa.CheckConstraint(
            "resource_type IN ('product', 'variation')", name="ck_publication_resource"
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    channel_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    resource_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    parent_external_id: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    document: Mapped[dict] = mapped_column(JSONB, nullable=False)
    revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    last_run_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
