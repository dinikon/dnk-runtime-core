import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class SkuModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Статическая tenant-модель SKU без отдельного поля tenant_id."""

    __tablename__ = "skus"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_skus"),
        sa.UniqueConstraint("code", name="uq_skus_code"),
        sa.CheckConstraint(
            "char_length(code) BETWEEN 1 AND 128 AND code = btrim(code) "
            "AND code !~ '[[:cntrl:]]'",
            name="ck_skus_code",
        ),
        sa.CheckConstraint(
            "char_length(btrim(title)) BETWEEN 1 AND 255",
            name="ck_skus_title",
        ),
    )

    code: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
