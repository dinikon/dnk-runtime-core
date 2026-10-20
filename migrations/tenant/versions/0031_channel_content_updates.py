"""Ручной предпросмотр и фоновое обновление текстов существующих публикаций."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0031_channel_content_updates"
down_revision = "0030_channel_publication_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт общий корень исходящей операции и принадлежащие ему позиции."""
    op.create_table(
        "channel_content_update_runs",
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
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("sdk_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preview_hash", sa.String(64), nullable=True),
        sa.CheckConstraint(
            "revision > 0 AND sequence >= 0 AND generation >= 0 AND sdk_version > 0",
            name="ck_content_update_revision",
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name="ck_content_update_expiration"
        ),
        sa.CheckConstraint(
            "status IN ('preparing','ready','blocked','queued','running','succeeded','partial','failed','stale')",
            name="ck_content_update_status",
        ),
    )
    op.create_index(
        "ix_content_update_channel_created",
        "channel_content_update_runs",
        ["channel_id", "created_at", "id"],
    )
    op.create_table(
        "channel_content_update_items",
        sa.Column(
            "run_id",
            sa.UUID(),
            sa.ForeignKey("channel_content_update_runs.id", ondelete="CASCADE"),
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
        sa.Column("binding_revision", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("provider_context", JSONB(), nullable=False),
        sa.Column("desired", JSONB(), nullable=False),
        sa.Column("observed", JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("issues", JSONB(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "binding_revision > 0 AND attempts >= 0",
            name="ck_content_update_item_revision",
        ),
        sa.CheckConstraint(
            "status IN ('preview_pending','ready','blocked','unchanged','pending','sending','verifying','succeeded','failed','unknown','stale','reconciling')",
            name="ck_content_update_item_status",
        ),
    )
    op.create_index(
        "ix_content_update_item_publication",
        "channel_content_update_items",
        ["publication_id", "run_id"],
    )


def downgrade() -> None:
    """Удаляет только историю контентных операций; каталог и связи сохраняются."""
    op.drop_table("channel_content_update_items")
    op.drop_table("channel_content_update_runs")
