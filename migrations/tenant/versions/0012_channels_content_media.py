"""Доступ площадок к изображениям и повторное использование внешних media ID."""

from alembic import op
import sqlalchemy as sa

revision = "0012_channels_content_media"
down_revision = "0011_channels_representations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет одну tenant-таблицу без публикации существующих файлов."""
    op.create_table(
        "channel_content_media",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("channel_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_id", sa.UUID(), nullable=False),
        sa.Column("source_fingerprint", sa.Text(), nullable=False),
        sa.Column("metadata_fingerprint", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("access_token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("access_token_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("access_revoked_at", sa.DateTime(timezone=True)),
        sa.Column("remote_media_id", sa.Text()),
        sa.Column("transfer_status", sa.Text(), nullable=False),
        sa.Column("current_operation_id", sa.UUID()),
        sa.Column("error_code", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "connection_id",
            "file_id",
            "source_fingerprint",
            "metadata_fingerprint",
            name="uq_content_media_variant",
        ),
    )
    op.create_index("ix_content_media_file", "channel_content_media", ["file_id"])


def downgrade() -> None:
    """Удаляет только доступ и кеш media, не затрагивая Files и площадку."""
    op.drop_table("channel_content_media")
