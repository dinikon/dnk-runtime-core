import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class AttributeModel(EntityAuditMixin, AudienceMixin, TenantBase):
    __tablename__ = "catalog_attributes"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_catalog_attributes"),
        sa.UniqueConstraint("code", name="uq_catalog_attributes_code"),
        sa.CheckConstraint("type = 'SELECT'", name="ck_catalog_attributes_type"),
    )

    code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    type: Mapped[str] = mapped_column(sa.String(16), nullable=False)
