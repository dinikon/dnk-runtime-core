from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from modules.shared.db import StringUUID
from modules.shared.db.base import TenantBase
from modules.shared.db.mixins import TenantSystemMixin


class DealORM(TenantBase, TenantSystemMixin):
    __tablename__ = "crm_deals"

    assigned_user_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
