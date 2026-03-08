from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from modules.shared.db import StringUUID
from modules.shared.db.base import TenantBase
from modules.shared.db.mixins import TenantSystemMixin


class LeadORM(TenantBase, TenantSystemMixin):
    __tablename__ = "crm_leads"

    assigned_user_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    contact_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("crm_contacts.id"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("crm_companies.id"),
        nullable=True,
        index=True,
    )
