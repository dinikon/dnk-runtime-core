"""Restore the domain registry in versioned databases missing the table."""

from alembic import op
import sqlalchemy as sa

revision = "0003_restore_tenant_domains"
down_revision = "0002_control_plane"
branch_labels = None
depends_on = None


def upgrade():
    # The original baseline already creates this table on fresh installations.
    # Leave an existing registry, including all domain records, untouched.
    if sa.inspect(op.get_bind()).has_table("tenant_domains", schema="public"):
        return

    op.create_table(
        "tenant_domains",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("service_type", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("base_path", sa.String(255), nullable=True),
        sa.Column("auth_mode", sa.String(32), nullable=True),
        sa.Column(
            "status", sa.String(32), server_default=sa.text("'active'"), nullable=False
        ),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("is_wildcard", sa.Boolean(), nullable=False),
        sa.Column("parent_domain", sa.String(255), nullable=True),
        sa.Column(
            "verification_status",
            sa.String(32),
            server_default=sa.text("'verified'"),
            nullable=False,
        ),
        sa.Column(
            "tls_mode",
            sa.String(32),
            server_default=sa.text("'managed'"),
            nullable=False,
        ),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["public.tenants.id"]),
        sa.UniqueConstraint(
            "tenant_id",
            "service_type",
            "host",
            "base_path",
            name="uq_saas_tenant_service_domain",
        ),
        schema="public",
    )
    for column in ("host", "is_primary", "kind", "service_type", "status", "tenant_id"):
        op.create_index(
            f"ix_tenant_domains_{column}",
            "tenant_domains",
            [column],
            unique=column == "host",
            schema="public",
        )


def downgrade():
    raise RuntimeError(
        "Public schema downgrade is intentionally unsupported; preserve tenant data."
    )
