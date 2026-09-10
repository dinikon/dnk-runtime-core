"""Create the first static tenant table: warehouses."""

from alembic import op
import sqlalchemy as sa

revision = "0001_warehouses"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт склады в схеме, выбранной migration environment."""
    op.create_table(
        "warehouses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_warehouses"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["warehouses.id"],
            name="fk_warehouses_parent_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("parent_id <> id", name="ck_warehouses_parent_not_self"),
    )
    op.create_index("ix_warehouses_parent_id", "warehouses", ["parent_id"])


def downgrade() -> None:
    """Удаляет таблицу складов, сохраняя tenant-схему."""
    op.drop_index("ix_warehouses_parent_id", table_name="warehouses")
    op.drop_table("warehouses")
