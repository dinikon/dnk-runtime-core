"""Состояние последней операции импорта в существующем ContentFeed."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0015_channels_feed_import"
down_revision = "0014_channels_content_feeds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет idle-состояние без автоматического запуска существующих фидов."""
    op.add_column(
        "channel_content_feeds",
        sa.Column(
            "delivery_schema",
            sa.Text(),
            nullable=False,
            server_default="content_feed_delivery.v1",
        ),
    )
    op.add_column(
        "channel_content_feeds",
        sa.Column(
            "delivery_state",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "channel_content_feeds",
        sa.Column("delivery_request_encrypted", sa.LargeBinary()),
    )


def downgrade() -> None:
    """Удаляет только состояние импорта, сохраняя настройки и доступ фидов."""
    op.drop_column("channel_content_feeds", "delivery_request_encrypted")
    op.drop_column("channel_content_feeds", "delivery_state")
    op.drop_column("channel_content_feeds", "delivery_schema")
