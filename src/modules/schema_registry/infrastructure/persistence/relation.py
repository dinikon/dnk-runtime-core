from datetime import datetime
from uuid import UUID

import uuid6
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db import Base, PortableJSON, StringUUID


class RelationORM(Base):
    """SQLAlchemy-модель metadata relation между runtime-объектами."""

    __tablename__ = "relations"

    id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    tenant_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    data_source_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(63), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)

    source_object_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("objects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    target_object_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("objects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    owning_object_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        ForeignKey("objects.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    fk_field_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        ForeignKey("fields.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    referenced_object_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        ForeignKey("objects.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    referenced_field_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        ForeignKey("fields.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    source_relation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_relation_name: Mapped[str] = mapped_column(String(255), nullable=False)

    relation_table_name: Mapped[str | None] = mapped_column(String(63), nullable=True)
    source_join_column_name: Mapped[str | None] = mapped_column(
        String(63),
        nullable=True,
    )
    target_join_column_name: Mapped[str | None] = mapped_column(
        String(63),
        nullable=True,
    )

    on_delete: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="restrict",
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_unique: Mapped[bool] = mapped_column(Boolean, nullable=False)
    kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="standard",
    )
    settings: Mapped[dict[str, str]] = mapped_column(PortableJSON, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_relations_tenant_name"),
    )
