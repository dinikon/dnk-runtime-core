"""Намерение пользователя для представления существующей группы публикаций."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_channels_representations"
down_revision = "0010_channels_stock_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт единственную таблицу без заполнения пустых представлений."""
    op.create_table(
        "channel_product_representations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "binding_group_id",
            sa.UUID(),
            sa.ForeignKey("channel_catalog_binding_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "export_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("overrides_schema", sa.Text(), nullable=False),
        sa.Column("overrides_data", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.UniqueConstraint("binding_group_id", name="uq_representation_binding_group"),
    )


def downgrade() -> None:
    """Удаляет только представления, сохраняя Catalog, группы и публикации."""
    op.drop_table("channel_product_representations")
