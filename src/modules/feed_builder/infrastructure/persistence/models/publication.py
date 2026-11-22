from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from src.modules.feed_builder.application.feed.types import JsonObject


class FeedPublicationModel(AudienceMixin, TenantBase):
    """Хранит участие позиции отдельно от Feed и внутренних таблиц Catalog."""

    __tablename__ = "fb_publications"
    __table_args__ = (
        sa.UniqueConstraint(
            "feed_id",
            "catalog_item_id",
            "catalog_variant_id",
            name="uq_fb_publications_reference",
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','ENABLED','PAUSED','ARCHIVED')",
            name="ck_fb_publications_status",
        ),
        sa.CheckConstraint("row_version >= 1", name="ck_fb_publications_version"),
        sa.CheckConstraint("updated_at >= created_at", name="ck_fb_publications_dates"),
        sa.CheckConstraint(
            "catalog_variant_id IS NULL OR catalog_variant_id <> catalog_item_id",
            name="ck_fb_publications_reference",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(overrides) = 'object'", name="ck_fb_publications_overrides"
        ),
        sa.Index(
            "ix_fb_publications_feed_status", "feed_id", "status", "created_at", "id"
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    feed_id: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.fb_feeds.id"), nullable=False
    )
    catalog_item_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    catalog_variant_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    row_version: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    overrides: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
