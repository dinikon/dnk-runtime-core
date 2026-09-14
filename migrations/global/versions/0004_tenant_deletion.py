"""Durable tenant deletion barrier and minimal completion receipts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_tenant_deletion"
down_revision = "0003_restore_tenant_domains"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cp_tenant_deletions",
        sa.Column("core_tenant_id", sa.UUID(), primary_key=True),
        sa.Column("runtime_tenant_id", sa.UUID(), unique=True),
        sa.Column("operation_id", sa.UUID(), unique=True, nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("command", postgresql.JSONB(), nullable=True),
        sa.Column("command_hash", sa.String(64), nullable=False),
        sa.Column("creation_succeeded", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('deletion_pending','blocked','purging','deleted')"
        ),
        schema="public",
    )


def downgrade():
    raise RuntimeError("Deletion receipts must survive application rollback.")
