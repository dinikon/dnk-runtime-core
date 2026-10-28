"""Хранение групп и принадлежащих им сопоставлений без бизнес-CHECK."""

from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogBindingGroupModel(TenantBase):
    """Заголовок независимой группы; Catalog IDs не являются чужими FK."""

    __tablename__ = "channel_catalog_binding_groups"
    __table_args__ = (
        sa.UniqueConstraint("publication_root_id", name="uq_binding_publication_root"),
        sa.Index("ix_binding_catalog_connection", "catalog_root_id", "connection_id"),
        sa.Index("ix_binding_connection_created", "connection_id", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    connection_id: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.channel_connections.id", ondelete="CASCADE")
    )
    catalog_root_id: Mapped[UUID] = mapped_column(StringUUID)
    mode: Mapped[str] = mapped_column(sa.String(32))
    publication_root_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            "tenant.channel_external_publications.id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    revision: Mapped[int] = mapped_column(sa.Integer)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(StringUUID)
    updated_by: Mapped[UUID] = mapped_column(StringUUID)
