from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db import Base, StringUUID


class DataSourceORM(Base):
    """SQLAlchemy-модель metadata datasource tenant runtime-схемы."""

    __tablename__ = "data_sources"

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
    tenant_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    data_source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=sa.text("'postgres'"),
    )
    schema_name: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        unique=True,
        index=True,
    )
    connection_dsn: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_data_sources_tenant_id"),)
