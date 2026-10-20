"""Полное содержимое публикации и временные файлы явного импорта в Catalog."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0030_channel_publication_imports"
down_revision = "0029_channels_catalog_bindings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет одну общую таблицу процесса без provider-specific DDL."""
    op.create_table(
        "channel_publication_import_preparations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "publication_id",
            sa.UUID(),
            sa.ForeignKey("channel_external_publications.id"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("connection_generation", sa.Integer(), nullable=False),
        sa.Column("observed_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("snapshot", JSONB(), nullable=True),
        sa.Column("media", JSONB(), nullable=False),
        sa.Column("error_code", sa.String(150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_image_ids", JSONB(), nullable=False),
        sa.CheckConstraint(
            "revision > 0 AND sequence >= 0 AND observed_revision > 0 AND connection_generation >= 0",
            name="ck_channel_import_revision",
        ),
        sa.CheckConstraint(
            "status IN ('queued','reading','images','ready','error','consumed','expired','cancelled')",
            name="ck_channel_import_status",
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name="ck_channel_import_expiration"
        ),
    )
    op.create_index(
        "ix_channel_import_expiration",
        "channel_publication_import_preparations",
        ["expires_at", "id"],
    )
    op.create_index(
        "ix_channel_import_publication",
        "channel_publication_import_preparations",
        ["publication_id", "actor_id"],
    )


def downgrade() -> None:
    """Удаляет состояние подготовки, сохраняя созданные Catalog и Files."""
    op.drop_table("channel_publication_import_preparations")
