from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductTypeContentBlockModel(TenantBase):
    __tablename__ = "catalog_product_type_content_blocks"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "product_type_id",
            "scope",
            "block_id",
            name="pk_catalog_product_type_content_blocks",
        ),
        sa.ForeignKeyConstraint(
            ["product_type_id"],
            ["tenant.catalog_product_types.id"],
            name="fk_catalog_product_type_blocks_type",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["tenant.catalog_content_block_definitions.id"],
            name="fk_catalog_product_type_blocks_block",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "product_type_id",
            "scope",
            "position",
            name="uq_catalog_product_type_blocks_position",
        ),
        sa.CheckConstraint(
            "scope IN ('product', 'variant')",
            name="ck_catalog_product_type_blocks_scope",
        ),
        sa.CheckConstraint(
            "position >= 0", name="ck_catalog_product_type_blocks_position"
        ),
    )

    product_type_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    scope: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    block_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    required: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
