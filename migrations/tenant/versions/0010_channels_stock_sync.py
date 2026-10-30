"""Разрешение отправки и состояние количественной синхронизации Channels."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_channels_stock_sync"
down_revision = "0009_channels_catalog_bindings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Новые подключения и существующие каналы начинают с запрещённой отправкой."""
    op.execute(sa.text("""
        UPDATE channel_connections AS connection
        SET settings = connection.settings || jsonb_build_object(
            'stock_sync', jsonb_build_object(
                'allow_export', false,
                'revision', 1,
                'changed_at', channel.created_at
            )
        )
        FROM channels AS channel
        WHERE channel.id = connection.channel_id
    """))
    op.create_table(
        "channel_stock_sync_states",
        sa.Column(
            "publication_id",
            sa.UUID(),
            sa.ForeignKey("channel_external_publications.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("channel_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("operation_id", sa.UUID(), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("config_revision", sa.Integer(), nullable=False),
        sa.Column("policy_revision", sa.Integer(), nullable=False),
        sa.Column(
            "binding_group_id",
            sa.UUID(),
            sa.ForeignKey("channel_catalog_binding_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("binding_revision", sa.Integer(), nullable=False),
        sa.Column("observed", postgresql.JSONB(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("desired_quantity", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_channel_stock_binding", "channel_stock_sync_states", ["binding_group_id"]
    )


def downgrade() -> None:
    """Удаляет только настройки и состояния этого среза."""
    op.drop_table("channel_stock_sync_states")
    op.execute(
        sa.text("UPDATE channel_connections SET settings = settings - 'stock_sync'")
    )
