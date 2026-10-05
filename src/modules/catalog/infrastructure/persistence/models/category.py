from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CategoryModel(EntityAuditMixin, AudienceMixin, TenantBase):
    __tablename__ = "catalog_categories"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_catalog_categories"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["tenant.catalog_categories.id"],
            name="fk_catalog_categories_parent",
            ondelete="RESTRICT",
        ),
        sa.Index("ix_catalog_categories_parent_id", "parent_id"),
    )

    parent_id: Mapped[UUID | None] = mapped_column(StringUUID)
