import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Карточка SIMPLE в схеме текущего tenant."""

    __tablename__ = "catalog_products"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_catalog_products"),
        sa.CheckConstraint("type = 'SIMPLE'", name="ck_catalog_products_type"),
    )

    type: Mapped[str] = mapped_column(sa.String(16), nullable=False)
