from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogItemCategoryModel(TenantBase):
    """Связывает корневую карточку с категорией и отмечает основное назначение."""

    __tablename__ = "catalog_item_categories"
    catalog_item_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.catalog_categories.id"), primary_key=True
    )
    is_default: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)
    __table_args__ = (
        sa.Index("ix_catalog_item_categories_category_id", "category_id"),
    )
