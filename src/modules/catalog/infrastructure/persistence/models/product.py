from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Tenant-хранение агрегата; бизнес-правила находятся в Domain."""

    __tablename__ = "catalog_products"
    __table_args__ = (
        sa.CheckConstraint("revision>0", name="ck_product_revision"),
        sa.CheckConstraint(
            "kind IN ('simple','variable')", name="ck_catalog_product_kind"
        ),
    )
    revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    kind: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    product_type_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_product_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
