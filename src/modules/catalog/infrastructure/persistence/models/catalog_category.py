from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogCategoryModel(TenantBase):
    """Хранит положение узла в дереве и исходный язык."""

    __tablename__ = "catalog_categories"
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    parent_id: Mapped[UUID | None] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.catalog_categories.id")
    )
    source_locale: Mapped[str] = mapped_column(sa.String(64))
    is_default: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)
    __table_args__ = (sa.Index("ix_catalog_categories_parent_id", "parent_id"),)
