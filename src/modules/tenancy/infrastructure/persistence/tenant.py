from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence import Base, PortableJSON
from src.modules.shared.infrastructure.persistence import StringUUID


class TenantModel(Base):
    """SQLAlchemy-модель tenant."""

    __tablename__ = "tenants"

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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default=sa.text("'active'"),
        index=True,
    )
    custom_config: Mapped[dict[str, Any] | None] = mapped_column(
        PortableJSON,
        nullable=True,
    )
