import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.tenant_base import TenantBase


class ContactModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Статическая tenant-модель CRM-контакта."""

    __tablename__ = "contacts"
    __table_args__ = (
        sa.CheckConstraint(
            "char_length(btrim(first_name)) BETWEEN 1 AND 255",
            name="ck_contacts_first_name",
        ),
        sa.CheckConstraint(
            "last_name IS NULL OR char_length(btrim(last_name)) BETWEEN 1 AND 255",
            name="ck_contacts_last_name",
        ),
        sa.CheckConstraint(
            "middle_name IS NULL OR char_length(btrim(middle_name)) BETWEEN 1 AND 255",
            name="ck_contacts_middle_name",
        ),
        sa.Index(
            "ix_contacts_name",
            "last_name",
            "first_name",
            "middle_name",
            "id",
        ),
    )

    first_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    last_name: Mapped[str | None] = mapped_column(sa.String(255))
    middle_name: Mapped[str | None] = mapped_column(sa.String(255))
