from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db.base import Base
from src.modules.shared.db.types import StringUUID


class RuntimeObjectMetadataModel(Base):
    __tablename__ = "runtime_object_metadata"

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
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    data_source_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("runtime_data_source_metadata.id"),
        nullable=False,
        index=True,
    )
    name_singular: Mapped[str] = mapped_column(String(63), nullable=False)
    name_plural: Mapped[str] = mapped_column(String(63), nullable=False)
    label_singular: Mapped[str] = mapped_column(String(255), nullable=False)
    label_plural: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )
    duplicate_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    shortcut: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ownership_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    allows_custom_fields: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "name_singular",
            name="uq_runtime_object_tenant_name",
        ),
    )


__all__ = ["RuntimeObjectMetadataModel"]
