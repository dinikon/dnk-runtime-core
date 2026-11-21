"""Дочерние варианты упаковки складской позиции."""

from alembic import op
import sqlalchemy as sa

revision = "0021_inventory_item_packagings"
down_revision = "0020_inventory_packaging_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет варианты упаковки с точным количеством, FK и уникальностью внутри SKU."""
    op.create_table(
        "inventory_item_packagings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inventory_item_id", sa.UUID(), nullable=False),
        sa.Column("packaging_type_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.Text(collation="C"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("content_quantity", sa.Numeric(), nullable=False),
        sa.Column("content_uom", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_item_packagings"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name="fk_item_packagings_item",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["packaging_type_id"],
            ["packaging_types.id"],
            name="fk_item_packagings_type",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "inventory_item_id", "code", name="uq_item_packagings_code"
        ),
        sa.UniqueConstraint(
            "inventory_item_id", "position", name="uq_item_packagings_position"
        ),
        sa.CheckConstraint(
            "char_length(btrim(code)) > 0", name="ck_item_packagings_code"
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name="ck_item_packagings_name"
        ),
        sa.CheckConstraint(
            "char_length(btrim(content_uom)) > 0", name="ck_item_packagings_uom"
        ),
        sa.CheckConstraint(
            "content_quantity > 0 AND content_quantity < 'Infinity'::numeric",
            name="ck_item_packagings_quantity",
        ),
        sa.CheckConstraint("position >= 0", name="ck_item_packagings_position"),
    )
    op.create_index(
        "ix_item_packagings_type", "inventory_item_packagings", ["packaging_type_id"]
    )


def downgrade() -> None:
    """Удаляет только дочернюю таблицу вариантов упаковки."""
    op.drop_index("ix_item_packagings_type", table_name="inventory_item_packagings")
    op.drop_table("inventory_item_packagings")
