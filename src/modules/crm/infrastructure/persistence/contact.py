from typing import Optional
from uuid import UUID

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from modules.shared.db import StringUUID
from modules.shared.db.base import TenantBase
from modules.shared.db.mixins import TenantSystemMixin


class ContactORM(TenantSystemMixin, TenantBase):
    __tablename__ = "crm_contacts"

    assigned_user_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)

    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
