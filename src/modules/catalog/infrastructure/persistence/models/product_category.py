from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductCategoryModel(TenantBase):
    __tablename__ = "catalog_product_categories"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "product_id", "category_id", name="pk_catalog_product_categories"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["tenant.catalog_products.id"],
            name="fk_catalog_product_categories_product",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["tenant.catalog_categories.id"],
            name="fk_catalog_product_categories_category",
            ondelete="RESTRICT",
        ),
        sa.Index("ix_catalog_product_categories_category_id", "category_id"),
        sa.Index(
            "uq_catalog_product_categories_primary",
            "product_id",
            unique=True,
            postgresql_where=sa.text("is_primary"),
        ),
    )

    product_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    category_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.false()
    )
