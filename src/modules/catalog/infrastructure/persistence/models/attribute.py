import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase

from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin


class AttributeModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Tenant-хранение enum-определения с отдельным жизненным циклом."""

    __tablename__ = "catalog_attributes"
    __table_args__ = (
        sa.CheckConstraint("revision>0", name="ck_catalog_attribute_revision"),
    )
    revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    code: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True)
