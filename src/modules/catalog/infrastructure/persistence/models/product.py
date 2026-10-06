import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Карточка товара в схеме текущего tenant."""

    __tablename__ = "catalog_products"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_catalog_products"),
        sa.CheckConstraint(
            "kind IN ('simple', 'variable')", name="ck_catalog_products_kind"
        ),
    )

    kind: Mapped[str] = mapped_column(sa.String(16), nullable=False)
