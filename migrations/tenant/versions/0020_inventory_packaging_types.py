"""Самостоятельный tenant-справочник форм-факторов тары."""

from alembic import op
import sqlalchemy as sa

revision = "0020_inventory_packaging_types"
down_revision = "0019_inventory_warehouses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт справочник с точной уникальностью кода в текущей tenant-схеме."""
    op.create_table(
        "packaging_types",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.Text(collation="C"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_packaging_types"),
        sa.UniqueConstraint("code", name="uq_packaging_types_code"),
        sa.CheckConstraint(
            "char_length(btrim(code)) > 0", name="ck_packaging_types_code"
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name="ck_packaging_types_name"
        ),
    )


def downgrade() -> None:
    """Удаляет только таблицу справочника типов тары."""
    op.drop_table("packaging_types")
