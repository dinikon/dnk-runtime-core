from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductAxisOptionModel(TenantBase):
    """Разрешённое значение оси с проверкой владельца option."""

    __tablename__ = "catalog_product_axis_options"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["product_id", "attribute_id"],
            [
                "tenant.catalog_product_axes.product_id",
                "tenant.catalog_product_axes.attribute_id",
            ],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["attribute_id", "option_id"],
            [
                "tenant.catalog_attribute_options.attribute_id",
                "tenant.catalog_attribute_options.id",
            ],
            ondelete="RESTRICT",
        ),
    )
    product_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    attribute_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    option_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
