from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class VariantModel(TenantBase):
    """Вариант товара; тип дублируется для составного FK и DB-ограничения SIMPLE."""

    __tablename__ = "catalog_variants"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_catalog_variants"),
        sa.ForeignKeyConstraint(
            ["product_id", "product_type"],
            ["tenant.catalog_products.id", "tenant.catalog_products.type"],
            name="fk_catalog_variants_product_type",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "product_id", "combination_key", name="uq_catalog_variants_combination"
        ),
        sa.Index(
            "uq_catalog_variants_simple_product",
            "product_id",
            unique=True,
            postgresql_where=sa.text("product_type = 'SIMPLE'"),
        ),
        sa.Index("ix_catalog_variants_sku_id", "sku_id"),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    product_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    product_type: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    combination_key: Mapped[str] = mapped_column(sa.Text(), nullable=False)
