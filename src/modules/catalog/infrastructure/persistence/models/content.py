from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductContentModel(TenantBase):
    """Перевод товара без tenant-wide выбора разрешённых локалей."""

    __tablename__ = "catalog_product_contents"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "product_id", "locale_code", name="pk_catalog_product_contents"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["tenant.catalog_products.id"],
            name="fk_catalog_product_contents_product",
            ondelete="CASCADE",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    locale_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
