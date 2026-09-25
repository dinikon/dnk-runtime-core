from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence import (
    TenantBase,
    AudienceMixin,
    StringUUID,
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


__all__ = ["ContactPointModel", "ContactPointBindingModel", "ContactPointLabelModel"]
