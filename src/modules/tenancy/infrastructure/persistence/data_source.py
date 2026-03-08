from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db.base import Base
from src.modules.shared.db.types import LongText, StringUUID


class TenantDataSourceModel(Base):
    __tablename__ = "data_sourses"

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
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    is_remote: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("'false'"),
    )
    dsn: Mapped[str | None] = mapped_column(LongText, nullable=True, default=None)
    schema: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
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

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_data_sourses_tenant_id"),
        UniqueConstraint("schema", name="uq_data_sourses_schema"),
    )
