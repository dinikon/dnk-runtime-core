from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db.base import Base
from src.modules.shared.db.types import StringUUID


class RelationMetadataModel(Base):
    __tablename__ = "relation_metadata"

    id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    source_object_metadata_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("object_metadata.id"),
        nullable=False,
        index=True,
    )
    source_field_metadata_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        ForeignKey("field_metadata.id"),
        nullable=True,
        index=True,
    )
    target_object_metadata_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("object_metadata.id"),
        nullable=False,
        index=True,
    )
    target_field_metadata_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        ForeignKey("field_metadata.id"),
        nullable=True,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reverse_name_field: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    reverse_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    junction_table_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        index=True,
    )
    on_delete: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("'false'"),
    )
    is_custom: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("'false'"),
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("'true'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("'true'"),
        index=True,
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

    __table_args__ = (
        UniqueConstraint(
            "source_field_metadata_id",
            name="uq_relation_metadata_source_field_metadata_id",
        ),
        UniqueConstraint(
            "junction_table_name",
            name="uq_relation_metadata_junction_table_name",
        ),
    )
