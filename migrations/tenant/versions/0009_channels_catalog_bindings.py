"""Группы привязки публикаций к Catalog."""

from alembic import op
import sqlalchemy as sa

revision = "0009_channels_catalog_bindings"
down_revision = "0008_catalog_variants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет только собственные таблицы Channels."""
    op.create_table(
        "channel_catalog_binding_groups",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("channel_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("catalog_root_id", sa.UUID(), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column(
            "publication_root_id",
            sa.UUID(),
            sa.ForeignKey(
                "channel_external_publications.id",
                deferrable=True,
                initially="DEFERRED",
            ),
            nullable=True,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.UniqueConstraint("publication_root_id", name="uq_binding_publication_root"),
    )
    op.create_index(
        "ix_binding_catalog_connection",
        "channel_catalog_binding_groups",
        ["catalog_root_id", "connection_id"],
    )
    op.create_index(
        "ix_binding_connection_created",
        "channel_catalog_binding_groups",
        ["connection_id", "created_at", "id"],
    )
    op.create_table(
        "channel_catalog_binding_items",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "group_id",
            sa.UUID(),
            sa.ForeignKey("channel_catalog_binding_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("catalog_position_id", sa.UUID(), nullable=False),
        sa.Column(
            "publication_id",
            sa.UUID(),
            sa.ForeignKey(
                "channel_external_publications.id",
                deferrable=True,
                initially="DEFERRED",
            ),
            nullable=False,
        ),
        sa.UniqueConstraint("publication_id", name="uq_binding_publication"),
        sa.UniqueConstraint(
            "group_id", "catalog_position_id", name="uq_binding_catalog_position"
        ),
    )
    op.create_index(
        "ix_binding_catalog_position",
        "channel_catalog_binding_items",
        ["catalog_position_id"],
    )


def downgrade() -> None:
    """Удаляет собственные связи без изменения Catalog и публикаций."""
    op.drop_table("channel_catalog_binding_items")
    op.drop_table("channel_catalog_binding_groups")
