"""Хранение групп и принадлежащих им сопоставлений без бизнес-CHECK."""

from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogBindingItemModel(TenantBase):
    """Явная пара, жизнь которой ограничена группой."""

    __tablename__ = "channel_catalog_binding_items"
    __table_args__ = (
        sa.UniqueConstraint("publication_id", name="uq_binding_publication"),
        sa.UniqueConstraint(
            "group_id", "catalog_position_id", name="uq_binding_catalog_position"
        ),
        sa.Index("ix_binding_catalog_position", "catalog_position_id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    group_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.channel_catalog_binding_groups.id", ondelete="CASCADE"),
    )
    catalog_position_id: Mapped[UUID] = mapped_column(StringUUID)
    publication_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            "tenant.channel_external_publications.id",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
