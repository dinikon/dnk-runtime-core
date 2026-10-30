"""Постоянные XML-фиды; существующие подключения не включают экспорт автоматически."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0014_channels_content_feeds"
down_revision = "0013_channels_content_deliveries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт только настройки и отзывной доступ, без копий XML."""
    op.create_table(
        "channel_content_feeds",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("channel_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope_key", sa.Text(), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_schema", sa.Text(), nullable=False),
        sa.Column("source_settings", JSONB(), nullable=False),
        sa.Column("source_url_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("access_token_hash", sa.LargeBinary()),
        sa.Column("access_token_encrypted", sa.LargeBinary()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.UniqueConstraint("connection_id", "scope_key", name="uq_content_feed_scope"),
        sa.CheckConstraint("revision > 0", name="ck_content_feed_revision"),
        sa.CheckConstraint(
            "(access_token_hash IS NULL) = (access_token_encrypted IS NULL)",
            name="ck_content_feed_token",
        ),
        sa.CheckConstraint(
            "NOT enabled OR access_token_hash IS NOT NULL",
            name="ck_content_feed_enabled",
        ),
    )


def downgrade() -> None:
    """Удаляет только локальные фиды и их доступ."""
    op.drop_table("channel_content_feeds")
