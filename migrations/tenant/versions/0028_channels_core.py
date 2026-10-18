"""Новое ядро Channels: Channel с единственным Connection и read initialization."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0028_channels_core"
down_revision = "0027_remove_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт новые таблицы после удаления исторического Channels."""
    op.create_table(
        "channels",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("platform_kind", sa.String(80), nullable=False),
        sa.Column(
            "is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "is_archived", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.CheckConstraint("revision > 0", name="ck_channels_revision"),
    )
    op.create_table(
        "channel_connections",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "channel_id", sa.UUID(), sa.ForeignKey("channels.id"), nullable=False
        ),
        sa.Column("endpoint", sa.String(2048), nullable=False),
        sa.Column("locales", JSONB(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("credentials_ciphertext", sa.Text(), nullable=False),
        sa.Column("candidate_ciphertext", sa.Text(), nullable=True),
        sa.Column("resource_identity", sa.String(1000), nullable=True),
        sa.Column("resource_key", sa.String(64), nullable=True),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("verification_job_id", sa.UUID(), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("is_paused", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(100), nullable=True),
        sa.Column("scope_limitations", JSONB(), nullable=False),
        sa.UniqueConstraint("channel_id", name="uq_channel_connections_channel"),
        sa.UniqueConstraint("resource_key", name="uq_channel_connections_resource"),
        sa.CheckConstraint("generation >= 0", name="ck_channel_connections_generation"),
    )
    op.create_table(
        "channel_sync_runs",
        sa.Column(
            "read_complete", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "channel_id", sa.UUID(), sa.ForeignKey("channels.id"), nullable=False
        ),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("channel_connections.id"),
            nullable=False,
        ),
        sa.Column(
            "operation",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'initialize_publications'"),
        ),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("checkpoint", JSONB(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("processed", sa.Integer(), nullable=False),
        sa.Column("invalid", sa.Integer(), nullable=False),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(100), nullable=True),
        sa.Column("limitations", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("request_keys", JSONB(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "sequence >= 0 AND processed >= 0 AND invalid >= 0 AND failures >= 0",
            name="ck_channel_runs_progress",
        ),
    )
    op.create_index(
        "ix_channel_runs_latest",
        "channel_sync_runs",
        ["connection_id", "created_at", "id"],
    )
    op.create_index(
        "uq_channel_runs_active",
        "channel_sync_runs",
        ["connection_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.create_table(
        "channel_external_publications",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("channel_connections.id"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column("external_sku", sa.String(512), nullable=True),
        sa.Column("price", sa.Numeric(30, 12), nullable=True),
        sa.Column("sale_price", sa.Numeric(30, 12), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("quantity", sa.Numeric(30, 12), nullable=True),
        sa.Column("stock_status", sa.String(30), nullable=False),
        sa.Column("title", sa.String(2000), nullable=True),
        sa.Column("title_locale", sa.String(100), nullable=True),
        sa.Column("main_image_url", sa.String(4096), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("warnings", JSONB(), nullable=False),
        sa.Column(
            "core_version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("extension_version", sa.String(100), nullable=False),
        sa.Column("extensions", JSONB(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("observed_revision", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_import_run_id",
            sa.UUID(),
            sa.ForeignKey("channel_sync_runs.id"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "connection_id",
            "resource_type",
            "external_id",
            name="uq_channel_external_publications_identity",
        ),
        sa.CheckConstraint(
            "observed_revision > 0 AND core_version = 1",
            name="ck_channel_publications_revision",
        ),
    )
    op.create_index(
        "ix_channel_publications_list",
        "channel_external_publications",
        ["connection_id", "id"],
    )
    op.create_index(
        "ix_channel_publications_sku",
        "channel_external_publications",
        ["connection_id", "external_sku"],
    )
    op.create_index(
        "ix_channel_publications_stock",
        "channel_external_publications",
        ["connection_id", "stock_status"],
    )


def downgrade() -> None:
    """Удаляет только новое хранение; старые данные не восстанавливает."""
    op.drop_table("channel_external_publications")
    op.drop_table("channel_sync_runs")
    op.drop_table("channel_connections")
    op.drop_table("channels")
