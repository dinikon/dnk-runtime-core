"""Пакетные исходящие операции, явное разрешение позиции и ежедневное расписание."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0033_channel_batch_exports"
down_revision = "0032_publication_payload_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет новые структуры без изменения публикаций, каталога и связей."""
    op.add_column(
        "channel_product_representations",
        sa.Column(
            "export_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_table(
        "channel_batch_exports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "channel_id", sa.UUID(), sa.ForeignKey("channels.id"), nullable=False
        ),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("channel_connections.id"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("remote_id", sa.String(200), nullable=True),
        sa.Column("artifact_hash", sa.String(64), nullable=True),
        sa.Column("artifact_size", sa.BigInteger(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("identity_cursor", sa.String(200), nullable=True),
        sa.CheckConstraint(
            "sequence >= 0 AND generation >= 0 AND attempts >= 0",
            name="ck_batch_export_counters",
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name="ck_batch_export_expiration"
        ),
        sa.CheckConstraint(
            "status IN ('preparing','building','checking','ready','submitting','processing','verifying','unknown','succeeded','partial','failed','empty')",
            name="ck_batch_export_status",
        ),
    )
    op.create_index(
        "uq_batch_export_active_connection",
        "channel_batch_exports",
        ["connection_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('preparing','building','checking','ready','submitting','processing','verifying','unknown')"
        ),
    )
    op.create_index(
        "ix_batch_export_channel_created",
        "channel_batch_exports",
        ["channel_id", "created_at", "id"],
    )
    op.create_table(
        "channel_batch_export_items",
        sa.Column(
            "run_id",
            sa.UUID(),
            sa.ForeignKey("channel_batch_exports.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "publication_id",
            sa.UUID(),
            sa.ForeignKey("channel_external_publications.id"),
            primary_key=True,
        ),
        sa.Column("catalog_item_id", sa.UUID(), nullable=False),
        sa.Column(
            "binding_id",
            sa.UUID(),
            sa.ForeignKey("channel_external_bindings.id"),
            nullable=False,
        ),
        sa.Column(
            "representation_id",
            sa.UUID(),
            sa.ForeignKey("channel_product_representations.id"),
            nullable=False,
        ),
        sa.Column("binding_revision", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("provider_context", JSONB(), nullable=False),
        sa.Column("desired", JSONB(), nullable=True),
        sa.Column("baseline", JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("issues", JSONB(), nullable=False),
        sa.Column("identity_key", sa.String(512), nullable=True),
        sa.Column("identity_count", sa.Integer(), nullable=False),
        sa.Column("identity_native_ok", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "binding_revision > 0 AND identity_count BETWEEN 0 AND 2",
            name="ck_batch_export_item_counters",
        ),
        sa.CheckConstraint(
            "status IN ('pending','ready','skipped','verified','failed','unknown')",
            name="ck_batch_export_item_status",
        ),
    )
    op.create_index(
        "ix_batch_export_item_work",
        "channel_batch_export_items",
        ["run_id", "status", "publication_id"],
    )
    op.create_index(
        "ix_batch_export_item_identity",
        "channel_batch_export_items",
        ["run_id", "identity_key"],
    )
    op.create_table(
        "channel_export_schedules",
        sa.Column(
            "channel_id", sa.UUID(), sa.ForeignKey("channels.id"), primary_key=True
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("hour", sa.Integer(), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("next_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "hour BETWEEN 0 AND 23 AND minute BETWEEN 0 AND 59 AND revision > 0",
            name="ck_export_schedule_time",
        ),
        sa.CheckConstraint(
            "enabled = (next_at IS NOT NULL)", name="ck_export_schedule_next"
        ),
    )


def downgrade() -> None:
    """Удаляет только данные исходящих пакетов и их policy."""
    op.drop_table("channel_export_schedules")
    op.drop_table("channel_batch_export_items")
    op.drop_table("channel_batch_exports")
    op.drop_column("channel_product_representations", "export_enabled")
