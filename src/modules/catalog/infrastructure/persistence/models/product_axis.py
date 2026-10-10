from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductAxisModel(TenantBase):
    """Разрешённая ось выбора внутри Product."""

    __tablename__ = "catalog_product_axes"
    __table_args__ = (
        sa.UniqueConstraint("product_id", "position", name="uq_catalog_axis_position"),
        sa.CheckConstraint("position>=0", name="ck_catalog_axis_position"),
    )
    product_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    attribute_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_attributes.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
