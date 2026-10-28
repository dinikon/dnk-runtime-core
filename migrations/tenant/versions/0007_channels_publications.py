"""Channels: запуски синхронизации и снимки внешних публикаций."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007_channels_publications"
down_revision = "0006_channels_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет хранение без SQL-правил ролей и переходов состояния."""
    op.create_table(
        "channel_sync_runs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("channel_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("config_revision", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("current_job_id", sa.UUID(), nullable=False),
        sa.Column("checkpoint_version", sa.Integer(), nullable=False),
        sa.Column("checkpoint", JSONB(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("pages_count", sa.Integer(), nullable=False),
        sa.Column("automatic", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_channel_sync_runs_connection",
        "channel_sync_runs",
        ["connection_id", "created_at", "id"],
    )
    op.create_table(
        "channel_external_publications",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("channel_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column(
            "parent_id",
            sa.UUID(),
            sa.ForeignKey(
                "channel_external_publications.id",
                deferrable=True,
                initially="DEFERRED",
            ),
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("raw_data", JSONB(), nullable=False),
        sa.Column("normalized_schema", sa.String(100), nullable=False),
        sa.Column("normalized_data", JSONB(), nullable=False),
        sa.Column("platform_schema", sa.String(100), nullable=False),
        sa.Column("platform_data", JSONB(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_sync_run_id",
            sa.UUID(),
            sa.ForeignKey(
                "channel_sync_runs.id", deferrable=True, initially="DEFERRED"
            ),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "connection_id",
            "resource_type",
            "external_id",
            name="uq_channel_publication_external_key",
        ),
    )
    op.create_index(
        "ix_channel_publications_parent",
        "channel_external_publications",
        ["parent_id", "id"],
    )
    op.create_index(
        "ix_channel_publications_connection",
        "channel_external_publications",
        ["connection_id", "id"],
    )
    op.create_index(
        "ix_channel_publications_run",
        "channel_external_publications",
        ["last_sync_run_id"],
    )


def downgrade() -> None:
    """Удаляет только хранение данного среза."""
    op.drop_table("channel_external_publications")
    op.drop_table("channel_sync_runs")
