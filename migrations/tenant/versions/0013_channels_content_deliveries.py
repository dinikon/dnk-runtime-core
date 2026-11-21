"""Ручная исходящая доставка контента существующих публикаций."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0013_channels_content_deliveries"
down_revision = "0012_channels_content_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет состояние целей; существующие представления не запускаются."""
    op.create_table(
        "channel_content_deliveries",
        sa.Column(
            "representation_id",
            sa.UUID(),
            sa.ForeignKey("channel_product_representations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "publication_id",
            sa.UUID(),
            sa.ForeignKey("channel_external_publications.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("requested_generation", sa.BigInteger(), nullable=False),
        sa.Column("sending_generation", sa.BigInteger()),
        sa.Column("applied_generation", sa.BigInteger()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("current_job_id", sa.UUID(), nullable=False),
        sa.Column("requested_context", JSONB(), nullable=False),
        sa.Column("prepared_schema", sa.Text()),
        sa.Column("prepared_request_encrypted", sa.LargeBinary()),
        sa.Column("prepared_context", JSONB()),
        sa.Column("prepared_hash", sa.Text()),
        sa.Column("last_applied_hash", sa.Text()),
        sa.Column("result", JSONB(), nullable=False),
        sa.Column("error_code", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_content_delivery_publication",
        "channel_content_deliveries",
        ["publication_id"],
    )
    op.create_index(
        "ix_content_delivery_pending",
        "channel_content_deliveries",
        ["status"],
        postgresql_where=sa.text("status IN ('queued', 'unknown')"),
    )


def downgrade() -> None:
    """Удаляет только локальные состояния, не меняя публикации площадки."""
    op.drop_table("channel_content_deliveries")
