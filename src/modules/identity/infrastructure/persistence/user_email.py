from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import DateTime, ForeignKey, Index, PrimaryKeyConstraint, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS
from src.modules.shared.infrastructure.persistence.tenant_base import TenantBase
from src.modules.shared.infrastructure.persistence import StringUUID


class UserEmailModel(TenantBase):
    """Email пользователя в той же tenant-схеме; структура управляется Alembic."""

    __tablename__ = "user_emails"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_user_emails"),
        Index("ix_user_emails_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(
        StringUUID, primary_key=True, default=uuid6.uuid7, nullable=False
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
    user_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey(f"{TENANT_SCHEMA_ALIAS}.users.id", name="fk_user_emails_user_id"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.text("'false'")
    )
    is_verified: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.text("'false'")
    )
    is_deleted: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.text("'false'")
    )
