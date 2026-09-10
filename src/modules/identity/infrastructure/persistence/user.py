from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import DateTime, Index, PrimaryKeyConstraint, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.tenant_base import TenantBase
from src.modules.shared.infrastructure.persistence import StringUUID


class UserModel(TenantBase):
    """Пользователь tenant; структура таблицы управляется Alembic."""

    __tablename__ = "users"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_users"),
        Index("ix_users_status", "status"),
    )

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
    status: Mapped[str] = mapped_column(
        String(255),
        server_default=sa.text("'active'"),
        nullable=False,
    )
    user_type: Mapped[str] = mapped_column(String(255))
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
    interface_language: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default="uk",
    )
    interface_theme: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default="system",
    )
    timezone: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default="Europe/Kyiv",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.current_timestamp(),
    )
    last_active_at: Mapped[datetime] = mapped_column(
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
