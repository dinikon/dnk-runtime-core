from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductCategoryModel(TenantBase):
    """Принадлежащее Product явное назначение category."""

    __tablename__ = "catalog_product_categories"
    product_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_categories.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    is_primary: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    __table_args__ = (
        sa.Index(
            "uq_catalog_primary_category",
            "product_id",
            unique=True,
            postgresql_where=sa.text("is_primary"),
        ),
    )
