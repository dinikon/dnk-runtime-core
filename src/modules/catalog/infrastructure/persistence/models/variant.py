from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class VariantModel(TenantBase):
    """Единственная продаваемая позиция SIMPLE-товара."""

    __tablename__ = "catalog_variants"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_catalog_variants"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["tenant.catalog_products.id"],
            name="fk_catalog_variants_product",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("product_id", name="uq_catalog_variants_product"),
        sa.Index("ix_catalog_variants_sku_id", "sku_id"),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    product_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    sku_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
