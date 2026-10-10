from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductAttributeValueModel(TenantBase):
    """Общее enum-значение Product, независимое от variation axes."""

    __tablename__ = "catalog_product_attribute_values"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["attribute_id", "option_id"],
            [
                "tenant.catalog_attribute_options.attribute_id",
                "tenant.catalog_attribute_options.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "product_id", "position", name="uq_catalog_attribute_value_position"
        ),
        sa.CheckConstraint("position>=0", name="ck_catalog_attribute_value_position"),
    )
    product_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    attribute_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    option_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    visible: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
