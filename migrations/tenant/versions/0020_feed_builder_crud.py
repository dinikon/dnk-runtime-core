"""Создаёт текущие Feed без ревизий, публикаций и генераций."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0020_feed_builder_crud"
down_revision = "0019_catalog_price_amounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт таблицу и ограничения первой рабочей вертикали Feed."""
    op.create_table(
        "fb_feeds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("row_version", sa.BigInteger(), nullable=False),
        sa.Column("schema_definition", postgresql.JSONB(), nullable=False),
        sa.Column("export_settings", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="fb_feeds_pkey"),
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
    )
    op.create_index(
        "ix_fb_feeds_status_updated", "fb_feeds", ["status", "updated_at", "id"]
    )


def downgrade() -> None:
    """Удаляет таблицу только при явном откате миграции."""
    op.drop_index("ix_fb_feeds_status_updated", table_name="fb_feeds")
    op.drop_table("fb_feeds")
