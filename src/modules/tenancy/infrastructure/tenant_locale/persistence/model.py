from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class TenantLocaleModel(TenantBase):
    """Выбранная локаль в схеме одного tenant."""

    __tablename__ = "tenant_locales"
    __table_args__ = (sa.PrimaryKeyConstraint("code", name="pk_tenant_locales"),)

    code: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
