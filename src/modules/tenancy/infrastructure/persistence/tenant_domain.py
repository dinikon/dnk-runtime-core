from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db.base import Base, PortableJSON
from src.modules.shared.db.types import StringUUID


class TenantDomainModel(Base):
    """SQLAlchemy-модель tenant domain/host."""

    __tablename__ = "tenant_domains"

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
    service_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    base_path: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    auth_mode: Mapped[str | None] = mapped_column(
        String(32), nullable=True, default=None
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default=sa.text("'active'"),
        index=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    is_wildcard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parent_domain: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="verified",
        server_default=sa.text("'verified'"),
    )
    tls_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="managed",
        server_default=sa.text("'managed'"),
    )
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(
        PortableJSON, nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
        onupdate=func.current_timestamp(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "service_type",
            "host",
            "base_path",
            name="uq_saas_tenant_service_domain",
        ),
    )
