from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db.base import Base
from src.modules.shared.db.types import StringUUID


class UserEmailModel(Base):
    """SQLAlchemy-модель email-адреса пользователя identity."""

    __tablename__ = "user_emails"

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
        StringUUID, ForeignKey("users.id"), nullable=False, index=True
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
