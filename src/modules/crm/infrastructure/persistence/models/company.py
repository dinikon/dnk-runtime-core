import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.tenant_base import TenantBase


class CompanyModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Статическая tenant-модель CRM-компании."""

    __tablename__ = "companies"
    __table_args__ = (
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_companies_name",
        ),
        sa.Index("ix_companies_name", "name", "id"),
    )

    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
