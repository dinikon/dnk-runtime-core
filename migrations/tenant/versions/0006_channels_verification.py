"""Channels: один канал, одно подключение и текущая проверка магазина."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006_channels_verification"
down_revision = "0005_catalog_import_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет две таблицы в tenant search_path без изменения baseline."""
    op.create_table(
        "channels",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("platform_kind", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint("revision > 0", name="ck_channels_revision"),
        sa.CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 255", name="ck_channels_name"
        ),
    )
    op.create_index("ix_channels_list", "channels", ["updated_at", "id"])
    op.create_table(
        "channel_connections",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "channel_id",
            sa.UUID(),
            sa.ForeignKey("channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("config_version", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("settings", JSONB(), nullable=False),
        sa.Column("encrypted_credentials", sa.LargeBinary(), nullable=False),
        sa.Column("config_revision", sa.Integer(), nullable=False),
        sa.Column("identity_namespace", sa.String(100)),
        sa.Column("identity_key", sa.String(2048)),
        sa.Column("verification", JSONB(), nullable=False),
        sa.UniqueConstraint("channel_id", name="uq_channel_connections_channel"),
        sa.UniqueConstraint(
            "identity_namespace", "identity_key", name="uq_channel_connections_identity"
        ),
        sa.CheckConstraint(
            "config_revision > 0 AND config_version > 0",
            name="ck_channel_connections_revision",
        ),
        sa.CheckConstraint(
            "(identity_namespace IS NULL) = (identity_key IS NULL)",
            name="ck_channel_connections_identity",
        ),
    )


def downgrade() -> None:
    """Удаляет только таблицы первого среза Channels."""
    op.drop_table("channel_connections")
    op.drop_table("channels")
