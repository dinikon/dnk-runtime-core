from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db.base import Base
from src.modules.shared.db.types import StringUUID


class RuntimeDataSourceMetadataModel(Base):
    __tablename__ = "runtime_data_source_metadata"

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
    source_type: Mapped[str] = mapped_column(
        "type",
        String(32),
        nullable=False,
        server_default=sa.text("'postgresql'"),
        index=True,
    )
    schema: Mapped[str] = mapped_column(String(36), nullable=False)
    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        server_default=sa.text("''"),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "schema", name="uq_runtime_ds_tenant_schema"),
    )


__all__ = ["RuntimeDataSourceMetadataModel"]
