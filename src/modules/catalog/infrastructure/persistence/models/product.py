from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Карточка товара в схеме текущего tenant."""

    __tablename__ = "catalog_products"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_catalog_products"),
        sa.CheckConstraint(
            "kind IN ('simple', 'variable')", name="ck_catalog_products_kind"
        ),
        sa.ForeignKeyConstraint(
            ["product_type_id"],
            ["tenant.catalog_product_types.id"],
            name="fk_catalog_products_product_type",
            ondelete="RESTRICT",
        ),
    )

    kind: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    product_type_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
