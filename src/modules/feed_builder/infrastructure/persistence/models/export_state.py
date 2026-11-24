from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class FeedExportStateModel(TenantBase):
    """Хранит текущее состояние в одной строке фида."""

    __tablename__ = "fb_export_states"
    __table_args__ = (
        sa.CheckConstraint(
            "job_status IN ('PENDING','RUNNING')", name="ck_fb_export_job"
        ),
        sa.CheckConstraint(
            "last_outcome IN ('PUBLISHED','REJECTED','FAILED')",
            name="ck_fb_export_outcome",
        ),
        sa.CheckConstraint(
            "active_format IN ('csv','xml')", name="ck_fb_export_format"
        ),
        sa.Index("ix_fb_export_active_file", "active_file_id"),
    )

    feed_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.fb_feeds.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    job_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    job_status: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    requested_by: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    job_as_of: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    definition_snapshot: Mapped[JsonObject | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    last_completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    last_as_of: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    last_validation_policy: Mapped[str | None] = mapped_column(
        sa.String(16), nullable=True
    )
    last_outcome: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    last_reason_code: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    last_is_complete: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    total_items: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    valid_items: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    warning_items: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    rejected_items: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    active_file_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    active_format: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    active_as_of: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    active_published_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )


class FeedExportIssueModel(TenantBase):
    """Хранит диагностики только последней проверки."""

    __tablename__ = "fb_export_issues"
    __table_args__ = (
        sa.CheckConstraint(
            "severity IN ('WARNING','ERROR')", name="ck_fb_export_issue_severity"
        ),
        sa.Index("ix_fb_export_issues_feed", "feed_id", "id"),
        sa.Index("ix_fb_export_issues_severity", "feed_id", "severity", "id"),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, primary_key=True)
    feed_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.fb_export_states.feed_id", ondelete="CASCADE"),
        nullable=False,
    )
    publication_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    field_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    rule_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    sku: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    severity: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    path: Mapped[list[str | int]] = mapped_column(JSONB, nullable=False)
