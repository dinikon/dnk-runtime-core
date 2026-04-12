from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db.base import Base
from src.modules.shared.db.types import StringUUID


class UserModel(Base):
    """SQLAlchemy-модель пользователя identity."""

    __tablename__ = "users"

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
    status: Mapped[str] = mapped_column(
        String(255),
        server_default=sa.text("'active'"),
        nullable=False,
        index=True,
    )
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        server_default=None,
    )
    avatar: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        server_default=None,
    )
    interface__language: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default="uk",
    )
    interface_theme: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        server_default="system",
    )
    timezone: Mapped[str | None] = mapped_column(
        String(255),
        nullable=False,
        server_default="Europe/Kyiv",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.current_timestamp(),
    )
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_login_ip: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        server_default=None,
    )
    initialized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=None
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
