from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db.base import Base, PortableJSON
from src.modules.shared.db.types import StringUUID


class RuntimeFieldMetadataModel(Base):
    __tablename__ = "runtime_field_metadata"

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
    object_metadata_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("runtime_object_metadata.id"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    field_type: Mapped[str] = mapped_column("type", String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(63), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    default_value: Mapped[object | None] = mapped_column(PortableJSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    options: Mapped[list[str]] = mapped_column(
        PortableJSON,
        nullable=False,
        server_default=sa.text("'[]'"),
    )
    settings: Mapped[dict[str, object]] = mapped_column(
        PortableJSON,
        nullable=False,
        server_default=sa.text("'{}'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=sa.text("true"),
        index=True,
    )
    is_nullable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )
    is_unique: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=sa.text("false"),
    )

    __table_args__ = (
        UniqueConstraint(
            "object_metadata_id",
            "name",
            name="uq_runtime_field_object_name",
        ),
    )


__all__ = ["RuntimeFieldMetadataModel"]
