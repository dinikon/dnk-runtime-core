from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence import (
    AudienceMixin,
    StringUUID,
    TenantBase,
)


class ContactPointLabelModel(AudienceMixin, TenantBase):
    """Подпись связи, архивируемая без удаления references."""

    __tablename__ = "contact_point_labels"
    __table_args__ = (
        sa.CheckConstraint(
            "type IN ('phone', 'email')", name="ck_contact_point_labels_type"
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 100",
            name="ck_contact_point_labels_name",
        ),
        sa.Index("ix_contact_point_labels_type", "type", "name", "id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    type: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.true()
    )
    created_by: Mapped[UUID | None] = mapped_column(StringUUID)
    updated_by: Mapped[UUID | None] = mapped_column(StringUUID)


__all__ = ["ContactPointLabelModel"]
