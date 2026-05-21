from datetime import datetime
from typing import Any
from uuid import UUID

import uuid6
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db import Base, PortableJSON, StringUUID


class ObjectFeatureConfigORM(Base):
    """SQLAlchemy-модель feature config runtime-объекта."""

    __tablename__ = "object_feature_config"

    object_feature_config_id: Mapped[UUID] = mapped_column(
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
        nullable=False,
        index=True,
    )
    object_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("objects.id"),
        nullable=False,
        index=True,
    )
    feature_code: Mapped[str] = mapped_column(String(63), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(PortableJSON, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    locked_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "object_id",
            "feature_code",
            name="uq_object_feature_config_tenant_object_feature",
        ),
    )
