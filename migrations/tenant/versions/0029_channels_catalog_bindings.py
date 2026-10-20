"""Привязки Channels и идемпотентное атомарное создание Catalog Draft."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0029_channels_catalog_bindings"
down_revision = "0028_channels_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт только собственные таблицы Channels без FK в Catalog."""
    op.add_column("channel_connections", sa.Column("settings", JSONB(), nullable=True))
    op.execute(
        "UPDATE channel_connections SET settings=jsonb_build_object('locales',locales,'currency',currency)"
    )
    op.alter_column("channel_connections", "settings", nullable=False)
    op.create_check_constraint(
        "ck_channel_connections_settings_object",
        "channel_connections",
        "jsonb_typeof(settings) = 'object'",
    )
    op.drop_column("channel_connections", "locales")
    op.drop_column("channel_connections", "currency")
    op.drop_constraint(
        "ck_channel_publications_revision",
        "channel_external_publications",
        type_="check",
    )
    op.drop_column("channel_external_publications", "core_version")
    op.create_check_constraint(
        "ck_channel_publications_revision",
        "channel_external_publications",
        "observed_revision > 0",
    )
    op.create_table(
        "channel_product_representations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("channel_connections.id"),
            nullable=False,
        ),
        sa.Column("catalog_item_id", sa.UUID(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "connection_id", "catalog_item_id", name="uq_channel_representation_pair"
        ),
        sa.CheckConstraint("revision>0", name="ck_channel_representation_revision"),
    )
    op.create_index(
        "ix_channel_product_representations_catalog_item_id",
        "channel_product_representations",
        ["catalog_item_id"],
    )
    op.create_table(
        "channel_external_bindings",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "representation_id",
            sa.UUID(),
            sa.ForeignKey("channel_product_representations.id"),
            nullable=False,
        ),
        sa.Column(
            "publication_id",
            sa.UUID(),
            sa.ForeignKey("channel_external_publications.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "(released_at IS NULL)=(released_by IS NULL)",
            name="ck_channel_binding_release",
        ),
    )
    op.create_index(
        "uq_channel_binding_publication_active",
        "channel_external_bindings",
        ["publication_id"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )
    op.create_index(
        "uq_channel_binding_representation_active",
        "channel_external_bindings",
        ["representation_id"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )
    op.create_table(
        "channel_catalog_creation_requests",
        sa.Column("request_key", sa.UUID(), primary_key=True),
        sa.Column(
            "publication_id",
            sa.UUID(),
            sa.ForeignKey("channel_external_publications.id"),
            nullable=False,
        ),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("observed_revision", sa.Integer(), nullable=False),
        sa.Column("catalog_item_id", sa.UUID(), nullable=False),
        sa.Column(
            "representation_id",
            sa.UUID(),
            sa.ForeignKey("channel_product_representations.id"),
            nullable=False,
        ),
        sa.Column(
            "binding_id",
            sa.UUID(),
            sa.ForeignKey("channel_external_bindings.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
    )


def downgrade() -> None:
    """Удаляет receipt и привязки прежде корней, не изменяя созданные товары."""
    op.drop_table("channel_catalog_creation_requests")
    op.drop_table("channel_external_bindings")
    op.drop_table("channel_product_representations")

    op.add_column("channel_connections", sa.Column("locales", JSONB(), nullable=True))
    op.add_column(
        "channel_connections", sa.Column("currency", sa.String(3), nullable=True)
    )
    op.execute(
        "UPDATE channel_connections SET locales=COALESCE(settings->'locales','[]'::jsonb), currency=settings->>'currency'"
    )
    op.alter_column("channel_connections", "locales", nullable=False)
    op.drop_column("channel_connections", "settings")
    op.drop_constraint(
        "ck_channel_publications_revision",
        "channel_external_publications",
        type_="check",
    )
    op.add_column(
        "channel_external_publications",
        sa.Column(
            "core_version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
    )
    op.create_check_constraint(
        "ck_channel_publications_revision",
        "channel_external_publications",
        "observed_revision > 0 AND core_version = 1",
    )
