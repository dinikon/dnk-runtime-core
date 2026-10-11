from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductTypeBlockModel(TenantBase):
    """Нормализованное tenant-хранение; инварианты находятся в Domain."""

    __tablename__ = "catalog_product_type_content_blocks"
    __table_args__ = (
        sa.UniqueConstraint(
            "product_type_id", "position", name="uq_catalog_type_block_position"
        ),
        sa.CheckConstraint("position>=0", name="ck_catalog_type_block_position"),
    )
    product_type_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_product_types.id", ondelete="CASCADE"),
        primary_key=True,
    )
    block_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            "tenant.catalog_content_block_definitions.id", ondelete="RESTRICT"
        ),
        primary_key=True,
    )
    required: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
