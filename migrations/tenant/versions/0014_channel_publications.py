"""Сохранённые Read карточки и фоновые импорты каналов."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0014_channel_publications"
down_revision = "0013_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет ревизию подключения, публикации и устойчивый прогресс импорта."""
    op.add_column(
        "channels",
        sa.Column(
            "connection_revision", sa.Integer(), server_default="1", nullable=False
        ),
    )
    op.create_table(
        "channel_publication_import_runs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "channel_id",
            sa.UUID(),
            sa.ForeignKey("channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("connection_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("checkpoint", JSONB(), nullable=False),
        sa.Column("pages", sa.Integer(), nullable=False),
        sa.Column("resources", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'partial', 'failed')",
            name="ck_publication_import_status",
        ),
        sa.CheckConstraint(
            "connection_revision > 0 AND pages >= 0 AND resources >= 0",
            name="ck_publication_import_progress",
        ),
    )
    op.create_index(
        "ix_publication_import_channel",
        "channel_publication_import_runs",
        ["channel_id", "connection_revision", "created_at"],
    )
    op.create_index(
        "uq_publication_import_active",
        "channel_publication_import_runs",
        ["channel_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.create_table(
        "channel_publications",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "channel_id",
            sa.UUID(),
            sa.ForeignKey("channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("connection_revision", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("parent_external_id", sa.String(255), nullable=True),
        sa.Column("raw_payload", JSONB(), nullable=False),
        sa.Column("document", JSONB(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("last_run_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "channel_id",
            "connection_revision",
            "resource_type",
            "external_id",
            name="uq_channel_publication_identity",
        ),
        sa.CheckConstraint(
            "connection_revision > 0 AND revision > 0", name="ck_publication_revision"
        ),
        sa.CheckConstraint(
            "resource_type IN ('product', 'variation')", name="ck_publication_resource"
        ),
    )
    op.create_index(
        "ix_channel_publication_list",
        "channel_publications",
        ["channel_id", "connection_revision", "resource_type", "id"],
    )
    op.create_index(
        "ix_channel_publication_parent",
        "channel_publications",
        ["channel_id", "connection_revision", "parent_external_id"],
    )


def downgrade() -> None:
    """Удаляет локальные снимки и прогресс, сохраняя настройки каналов."""
    op.drop_table("channel_publications")
    op.drop_table("channel_publication_import_runs")
    op.drop_column("channels", "connection_revision")
