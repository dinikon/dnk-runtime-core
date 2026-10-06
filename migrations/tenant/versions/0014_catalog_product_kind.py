"""Rename product type to kind and normalize its stored value."""

from alembic import op
import sqlalchemy as sa

revision = "0014_catalog_product_kind"
down_revision = "0013_catalog_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_catalog_products_type", "catalog_products", type_="check")
    op.alter_column(
        "catalog_products",
        "type",
        new_column_name="kind",
        existing_type=sa.String(16),
        existing_nullable=False,
    )
    op.execute("UPDATE catalog_products SET kind = 'simple' WHERE kind = 'SIMPLE'")
    op.create_check_constraint(
        "ck_catalog_products_kind", "catalog_products", "kind = 'simple'"
    )


def downgrade() -> None:
    op.drop_constraint("ck_catalog_products_kind", "catalog_products", type_="check")
    op.execute("UPDATE catalog_products SET kind = 'SIMPLE' WHERE kind = 'simple'")
    op.alter_column(
        "catalog_products",
        "kind",
        new_column_name="type",
        existing_type=sa.String(16),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_catalog_products_type", "catalog_products", "type = 'SIMPLE'"
    )
