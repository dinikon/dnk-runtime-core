from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
import uuid6
from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
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
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    data_source_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)

    name_singular: Mapped[str] = mapped_column(String(128), nullable=False)
    name_plural: Mapped[str] = mapped_column(String(128), nullable=False)
    label_singular: Mapped[str] = mapped_column(String(255), nullable=False)
    label_plural: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(LongText, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shortcut: Mapped[str | None] = mapped_column(String(64), nullable=True)

    is_remote: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("'false'"),
    )
    is_system: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("'false'"),
    )
    is_custom: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("'true'"),
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("'true'"),
    )
    is_ui_read_only: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("'false'"),
    )
    duplicate_criteria: Mapped[dict[str, object] | None] = mapped_column(
        PortableJSON,
        nullable=True,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_source_id",
            "name_singular",
            name="uq_object_metadata_tenant_source_name",
        ),
    )


class FieldMetadataModel(Base):
    __tablename__ = "field_metadata"

    id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    object_metadata_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("object_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    field_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(LongText, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_system: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'false'")
    )
    is_custom: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'true'")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'true'")
    )

    is_unique: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'false'")
    )
    is_index: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'false'")
    )
    is_nullable: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'true'")
    )
    is_ui_read_only: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'false'")
    )
    is_searchable: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'false'")
    )

    options: Mapped[dict[str, object] | None] = mapped_column(PortableJSON, nullable=True)
    settings: Mapped[dict[str, object] | None] = mapped_column(PortableJSON, nullable=True)
    default_value: Mapped[dict[str, object] | None] = mapped_column(
        PortableJSON, nullable=True
    )

    relation_target_object_id: Mapped[UUID | None] = mapped_column(
        StringUUID, nullable=True, index=True
    )
    relation_target_field_id: Mapped[UUID | None] = mapped_column(
        StringUUID, nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    __table_args__ = (
        UniqueConstraint(
            "object_metadata_id",
            "field_name",
            name="uq_field_metadata_object_field",
        ),
    )


class FieldStorageMetadataModel(Base):
    __tablename__ = "field_storage_metadata"

    id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    field_metadata_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("field_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_name: Mapped[str] = mapped_column(String(128), nullable=False)
    sql_type: Mapped[str] = mapped_column(String(128), nullable=False)
    is_nullable: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'true'")
    )
    is_indexed: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'false'")
    )
    is_unique: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'false'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    __table_args__ = (
        UniqueConstraint(
            "field_metadata_id",
            "column_name",
            name="uq_field_storage_field_column",
        ),
    )


class FieldOptionMetadataModel(Base):
    __tablename__ = "field_option_metadata"

    id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    field_metadata_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("field_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("'true'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    __table_args__ = (
        UniqueConstraint(
            "field_metadata_id",
            "code",
            name="uq_field_option_field_code",
        ),
    )


class SchemaVersionModel(Base):
    __tablename__ = "schema_version"

    id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    data_source_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    schema: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "schema",
            name="uq_schema_version_tenant_schema",
        ),
    )


class SchemaMigrationJournalModel(Base):
    __tablename__ = "schema_migration_journal"

    id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    data_source_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    schema: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    operation_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    operation_sql: Mapped[str] = mapped_column(LongText, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(LongText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "ix_schema_migration_journal_schema_created",
            "schema",
            "created_at",
        ),
    )

