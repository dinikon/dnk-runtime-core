import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductTypeModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Tenant-хранение агрегата; бизнес-правила находятся в Domain."""

    __tablename__ = "catalog_product_types"
    __table_args__ = (
        sa.CheckConstraint("revision>0", name="ck_product_type_revision"),
        sa.CheckConstraint("schema_version>0", name="ck_catalog_type_version"),
    )
    revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    code: Mapped[str] = mapped_column(sa.String(64), unique=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    schema_version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
