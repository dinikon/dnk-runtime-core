from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence import StringUUID, TenantBase


class ContactCompanyModel(TenantBase):
    """Хранение самостоятельной связи Contact–Company."""

    __tablename__ = "contact_companies"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["tenant.contacts.id"],
            name="fk_contact_companies_contact",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["tenant.companies.id"],
            name="fk_contact_companies_company",
            ondelete="CASCADE",
        ),
        sa.Index("ix_contact_companies_company", "company_id", "contact_id"),
    )
    contact_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    company_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
