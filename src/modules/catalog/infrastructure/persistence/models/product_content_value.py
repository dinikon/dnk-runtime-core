from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductContentValueModel(TenantBase):
    __tablename__ = "catalog_product_content_values"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "product_id",
            "locale_code",
            "block_id",
            name="pk_catalog_product_content_values",
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "locale_code"],
            [
                "tenant.catalog_product_contents.product_id",
                "tenant.catalog_product_contents.locale_code",
            ],
            name="fk_catalog_product_content_values_content",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["tenant.catalog_content_block_definitions.id"],
            name="fk_catalog_product_content_values_block",
            ondelete="RESTRICT",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    locale_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    block_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    value: Mapped[str] = mapped_column(sa.Text, nullable=False)
