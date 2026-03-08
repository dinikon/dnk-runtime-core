from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db.base import Base, PortableJSON
from src.modules.shared.db.types import LongText, StringUUID


class ObjectMetadataModel(Base):
    __tablename__ = "object_metadata"

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
    data_source_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("data_sourses.id"),
        nullable=False,
        index=True,
    )
    name_singular: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name_plural: Mapped[str] = mapped_column(String(255), nullable=False)
    label_singular: Mapped[str] = mapped_column(String(255), nullable=False)
    label_plural: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(
        LongText, nullable=True, default=None
    )
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    is_custom: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("'false'"),
    )
    is_remote: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("'false'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("'true'"),
        index=True,
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("'true'"),
        index=True,
    )
    is_ui_read_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("'false'"),
    )
    is_audit_logged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("'false'"),
    )
    is_searchable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("'true'"),
    )
    duplicate_criteria: Mapped[object | None] = mapped_column(
        PortableJSON,
        nullable=True,
        default=None,
    )
    shortcut: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None
    )
    label_identifier_field_metadata_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        nullable=True,
        default=None,
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

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "name_singular",
            name="uq_object_metadata_tenant_name_singular",
        ),
    )
