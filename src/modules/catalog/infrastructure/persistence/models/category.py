from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin


class CategoryModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Нормализованное tenant-хранение корня category."""

    __tablename__ = "catalog_categories"
    __table_args__ = (
        sa.CheckConstraint("revision>0", name="ck_catalog_category_revision"),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id", name="ck_catalog_category_parent"
        ),
    )
    revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
