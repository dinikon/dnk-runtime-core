from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence import (
    AudienceMixin,
    StringUUID,
    TenantBase,
)


class ContactPointBindingModel(AudienceMixin, TenantBase):
    """Полиморфная привязка точки к заблокированному владельцу."""

    __tablename__ = "contact_point_bindings"
    __table_args__ = (
        sa.UniqueConstraint(
            "model_key",
            "record_id",
            "contact_point_id",
            name="uq_contact_point_bindings_target_point",
        ),
        sa.CheckConstraint("position >= 0", name="ck_contact_point_bindings_position"),
        sa.Index(
            "ix_contact_point_bindings_target",
            "model_key",
            "record_id",
            "position",
            "id",
        ),
        sa.Index("ix_contact_point_bindings_point", "contact_point_id"),
        sa.Index("ix_contact_point_bindings_label", "label_id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    contact_point_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            "tenant.contact_points.id", name="fk_contact_point_bindings_point"
        ),
        nullable=False,
    )
    model_key: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    record_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    label_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            "tenant.contact_point_labels.id", name="fk_contact_point_bindings_label"
        ),
    )
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    created_by: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    updated_by: Mapped[UUID] = mapped_column(StringUUID, nullable=False)


__all__ = ["ContactPointBindingModel"]
