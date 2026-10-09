import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ContentBlockModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Tenant-хранение агрегата; бизнес-правила находятся в Domain."""

    __tablename__ = "catalog_content_block_definitions"
    __table_args__ = (
        sa.CheckConstraint("revision>0", name="ck_content_block_revision"),
        sa.CheckConstraint(
            "value_type IN ('text','rich_text')", name="ck_catalog_block_value_type"
        ),
    )
    revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    code: Mapped[str] = mapped_column(sa.String(64), unique=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    value_type: Mapped[str] = mapped_column(sa.String(20), nullable=False)
