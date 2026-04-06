from datetime import datetime
from uuid import UUID

import uuid6
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db import Base, PortableJSON, StringUUID


class FieldORM(Base):
    __tablename__ = "fields"

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
    object_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("objects.id"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type_code: Mapped[str] = mapped_column(String(32), nullable=False)
    field_type_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    field_type_literal_value: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    field_type_sql_preset: Mapped[str | None] = mapped_column(String(64), nullable=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    is_nullable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    default_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    options: Mapped[dict[str, str]] = mapped_column(PortableJSON, nullable=False)
    settings: Mapped[dict[str, str]] = mapped_column(PortableJSON, nullable=False)
