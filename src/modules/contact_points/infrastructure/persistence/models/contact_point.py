from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence import (
    AudienceMixin,
    StringUUID,
    TenantBase,
)


class ContactPointModel(AudienceMixin, TenantBase):
    """Канонический адрес внутри tenant-схемы."""

    __tablename__ = "contact_points"
    __table_args__ = (
        sa.UniqueConstraint("type", "canonical_value", name="uq_contact_points_value"),
        sa.CheckConstraint("type IN ('phone', 'email')", name="ck_contact_points_type"),
        sa.CheckConstraint(
            "char_length(btrim(canonical_value)) BETWEEN 1 AND 320",
            name="ck_contact_points_value",
        ),
        sa.CheckConstraint(
            "(type = 'phone' AND country_code IS NOT NULL AND char_length(country_code) = 2) OR (type = 'email' AND country_code IS NULL)",
            name="ck_contact_points_country",
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    type: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    canonical_value: Mapped[str] = mapped_column(sa.String(320), nullable=False)
    country_code: Mapped[str | None] = mapped_column(sa.String(2))
    created_by: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    updated_by: Mapped[UUID] = mapped_column(StringUUID, nullable=False)


__all__ = ["ContactPointModel"]
