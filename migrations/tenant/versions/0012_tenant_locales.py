"""Add a tenant-owned selection of system locales."""

from alembic import op
import sqlalchemy as sa

revision = "0012_tenant_locales"
down_revision = "0011_inventory_skus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт справочник выбора локалей в текущей tenant-схеме."""
    op.create_table(
        "tenant_locales",
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("code", name="pk_tenant_locales"),
    )


def downgrade() -> None:
    """Удаляет выбор локалей только текущего tenant."""
    op.drop_table("tenant_locales")
