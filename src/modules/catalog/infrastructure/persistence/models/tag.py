from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin


class TagModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Нормализованное tenant-хранение корня tag."""

    __tablename__ = "catalog_tags"
    __table_args__ = (sa.CheckConstraint("revision>0", name="ck_catalog_tag_revision"),)
    revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
