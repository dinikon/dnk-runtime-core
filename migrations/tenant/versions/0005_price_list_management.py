"""Add price-list archive lifecycle support."""

from alembic import op
import sqlalchemy as sa

revision = "0005_price_list_management"
down_revision = "0004_partner_price_lists"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "price_lists",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_constraint("ck_price_lists_status", "price_lists", type_="check")
    op.create_check_constraint(
        "ck_price_lists_status",
        "price_lists",
        "status IN ('draft','ready','active','paused','invalid','archived')",
    )


def downgrade():
    op.execute("UPDATE price_lists SET status = 'paused' WHERE status = 'archived'")
    op.drop_constraint("ck_price_lists_status", "price_lists", type_="check")
    op.create_check_constraint(
        "ck_price_lists_status",
        "price_lists",
        "status IN ('draft','ready','active','paused','invalid')",
    )
    op.drop_column("price_lists", "archived_at")
