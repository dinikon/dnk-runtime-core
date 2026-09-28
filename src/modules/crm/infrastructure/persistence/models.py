from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence import (
    AudienceMixin,
    StringUUID,
    TenantBase,
)


class CrmEntityMixin(AudienceMixin):
    """Общие идентификатор и actor audit для CRM-моделей."""

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True, nullable=False)
    created_by: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    updated_by: Mapped[UUID] = mapped_column(StringUUID, nullable=False)


class ContactModel(CrmEntityMixin, TenantBase):
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


class CompanyModel(CrmEntityMixin, TenantBase):
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


__all__ = ["CompanyModel", "ContactModel"]
