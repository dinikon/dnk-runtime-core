"""Versioned roles and resumable synchronization of existing cloud access."""

from alembic import op
import sqlalchemy as sa

revision = "0005_access_roles"
down_revision = "0004_tenant_deletion"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cp_access_projections", sa.Column("role", sa.String(16)), schema="public"
    )
    op.add_column(
        "cp_access_projections",
        sa.Column(
            "role_synced", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        schema="public",
    )
    op.add_column(
        "cp_access_projections",
        sa.Column("sync_attempted_at", sa.DateTime(timezone=True)),
        schema="public",
    )

    op.create_index(
        "cp_access_role_sync_idx",
        "cp_access_projections",
        ["sync_attempted_at"],
        schema="public",
        postgresql_where=sa.text("NOT role_synced"),
    )


def downgrade():
    op.drop_index(
        "cp_access_role_sync_idx", table_name="cp_access_projections", schema="public"
    )
    for name in ("sync_attempted_at", "role_synced", "role"):
        op.drop_column("cp_access_projections", name, schema="public")
