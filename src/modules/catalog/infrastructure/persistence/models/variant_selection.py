from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class VariantSelectionModel(TenantBase):
    """Выбор разрешённого option каждой оси принадлежащей позиции."""

    __tablename__ = "catalog_variant_selections"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["product_id", "variant_id"],
            ["tenant.catalog_variants.product_id", "tenant.catalog_variants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "attribute_id", "option_id"],
            [
                "tenant.catalog_product_axis_options.product_id",
                "tenant.catalog_product_axis_options.attribute_id",
                "tenant.catalog_product_axis_options.option_id",
            ],
            ondelete="RESTRICT",
        ),
    )
    variant_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    attribute_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    product_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    option_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
