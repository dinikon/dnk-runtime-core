"""Consumer-owned conversion snapshots, without backfilling historical facts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_offer_money"
down_revision = "0007_currency"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "partner_offer_money_snapshots",
        sa.Column(
            "state_id",
            sa.UUID(),
            sa.ForeignKey("partner_offer_states.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("business_date", sa.Date()),
        sa.Column("purchase_price", postgresql.JSONB()),
        sa.Column("rrp", postgresql.JSONB()),
        sa.Column("error_code", sa.String(64)),
        sa.CheckConstraint(
            "status IN ('converted','unavailable')", name="ck_offer_money_status"
        ),
        sa.CheckConstraint(
            "(status = 'converted' AND error_code IS NULL AND business_date IS NOT NULL) OR (status = 'unavailable' AND error_code IS NOT NULL)",
            name="ck_offer_money_result",
        ),
    )


def downgrade():
    op.drop_table("partner_offer_money_snapshots")
