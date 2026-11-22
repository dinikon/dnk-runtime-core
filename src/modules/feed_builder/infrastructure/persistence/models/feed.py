from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from src.modules.feed_builder.application.feed.types import JsonObject


class FeedModel(AudienceMixin, TenantBase):
    """Хранит один текущий Feed в tenant-схеме без таблиц ревизий."""

    __tablename__ = "fb_feeds"
    __table_args__ = (
        sa.UniqueConstraint("code", name="uq_fb_feeds_code"),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255", name="ck_fb_feeds_name"
        ),
        sa.CheckConstraint("code ~ '^[a-z][a-z0-9_-]{0,63}$'", name="ck_fb_feeds_code"),
        sa.CheckConstraint(
            "status IN ('DRAFT','ACTIVE','PAUSED','ARCHIVED')",
            name="ck_fb_feeds_status",
        ),
        sa.CheckConstraint("row_version >= 1", name="ck_fb_feeds_version"),
        sa.CheckConstraint("updated_at >= created_at", name="ck_fb_feeds_dates"),
        sa.CheckConstraint(
            "jsonb_typeof(schema_definition) = 'object'", name="ck_fb_feeds_schema"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(export_settings) = 'object'", name="ck_fb_feeds_settings"
        ),
        sa.Index("ix_fb_feeds_status_updated", "status", "updated_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    row_version: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    schema_definition: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
    export_settings: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
