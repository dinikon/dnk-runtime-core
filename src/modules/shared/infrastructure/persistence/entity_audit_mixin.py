from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID


class EntityAuditMixin:
    """Общие идентификатор сущности и идентификаторы авторов изменений."""

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True, nullable=False)
    created_by: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    updated_by: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
