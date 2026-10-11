from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogItemCategoryModel(TenantBase):
    """Нормализованное tenant-хранение; инварианты находятся в Domain."""

    __tablename__ = "catalog_item_categories"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["catalog_item_id", "required_kind"],
            ["tenant.catalog_item.id", "tenant.catalog_item.kind"],
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.Index(
            "uq_catalog_item_primary_category",
            "catalog_item_id",
            unique=True,
            postgresql_where=sa.text("is_primary"),
        ),
    )
    catalog_item_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_categories.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    required_kind: Mapped[str] = mapped_column(
        sa.String(20), sa.Computed("'simple'", persisted=True), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
