"""Добавляет сохранённый ассортимент Feed без проекций и генерации."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0021_feed_publications"
down_revision = "0020_feed_builder_crud"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт самостоятельные публикации и защиту идентичности SIMPLE/VARIANT."""
    op.create_table(
        "fb_publications",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("feed_id", sa.UUID(), sa.ForeignKey("fb_feeds.id"), nullable=False),
        sa.Column("catalog_item_id", sa.UUID(), nullable=False),
        sa.Column("catalog_variant_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("row_version", sa.BigInteger(), nullable=False),
        sa.Column("overrides", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
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
    )
    op.create_index(
        "ix_fb_publications_feed_status",
        "fb_publications",
        ["feed_id", "status", "created_at", "id"],
    )


def downgrade() -> None:
    """Удаляет ассортимент только при явном откате миграции."""
    op.drop_table("fb_publications")
