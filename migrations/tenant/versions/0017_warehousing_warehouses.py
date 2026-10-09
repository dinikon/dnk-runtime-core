"""Новая модель Warehousing: создание и чтение самостоятельного склада."""

from alembic import op
import sqlalchemy as sa

revision = "0017_warehousing_warehouses"
down_revision = "0016_remove_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт новые склады в tenant-схеме без восстановления исторических данных."""
    op.create_table(
        "warehousing_warehouses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("timezone", sa.String(128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
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
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_warehousing_warehouses"),
        sa.UniqueConstraint("code", name="uq_warehousing_warehouses_code"),
        sa.CheckConstraint(
            "char_length(code) BETWEEN 1 AND 64 AND code = upper(btrim(code))",
            name="ck_warehousing_warehouses_code",
        ),
        sa.CheckConstraint(
            "char_length(btrim(title)) BETWEEN 1 AND 255",
            name="ck_warehousing_warehouses_title",
        ),
        sa.CheckConstraint(
            "char_length(btrim(type)) BETWEEN 1 AND 64",
            name="ck_warehousing_warehouses_type",
        ),
        sa.CheckConstraint(
            "char_length(btrim(timezone)) BETWEEN 1 AND 128",
            name="ck_warehousing_warehouses_timezone",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'archived')",
            name="ck_warehousing_warehouses_status",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_warehousing_warehouses_revision"),
        sa.CheckConstraint(
            "updated_at >= created_at", name="ck_warehousing_warehouses_audit"
        ),
    )
    op.create_index(
        "ix_warehousing_warehouses_status_type_code",
        "warehousing_warehouses",
        ["status", "type", "code", "id"],
    )


def downgrade() -> None:
    """Удаляет только новую таблицу, не затрагивая историю старого Inventory."""
    op.drop_index(
        "ix_warehousing_warehouses_status_type_code",
        table_name="warehousing_warehouses",
    )
    op.drop_table("warehousing_warehouses")
