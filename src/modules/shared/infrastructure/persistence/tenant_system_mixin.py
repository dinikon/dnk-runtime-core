from __future__ import annotations

from uuid import UUID

import uuid6
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID


class TenantSystemMixin(AudienceMixin):
    """SQLAlchemy mixin для tenant-scoped системных сущностей."""

    id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    updated_by: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
