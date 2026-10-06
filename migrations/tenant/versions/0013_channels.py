"""Настройки каналов с защищённым хранением credentials."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0013_channels"
down_revision = "0012_catalog"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "channels",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("config_version", sa.Integer(), nullable=False),
        sa.Column("connection_settings", JSONB(), nullable=False),
        sa.Column("encrypted_secrets", sa.Text(), nullable=False),
        sa.Column("configured_secret_fields", JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
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
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_channels"),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255", name="ck_channel_name"
        ),
        sa.CheckConstraint("config_version >= 1", name="ck_channel_config_version"),
        sa.CheckConstraint(
            "status IN ('unverified', 'connected', 'error')", name="ck_channel_status"
        ),
    )


def downgrade():
    op.drop_table("channels")
