"""Add bounded price-list staging and keyset access indexes."""

from alembic import op
import sqlalchemy as sa

revision = "0006_price_list_streaming"
down_revision = "0005_price_list_management"
branch_labels = None
depends_on = None


def upgrade():
    """Adds staging outcome and indexes without rewriting existing history."""
    op.add_column(
        "price_list_sync_items",
        sa.Column(
            "quarantined", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    # Old successful staging contains only quarantine rows; preserve them.
    op.execute(
        "UPDATE price_list_sync_items SET quarantined = true WHERE sync_run_id IN (SELECT id FROM price_list_sync_runs WHERE status IN ('succeeded','partial'))"
    )
    op.create_index(
        "ix_partner_offers_list_id", "partner_offers", ["price_list_id", "id"]
    )
    op.create_index(
        "ix_offer_states_offer_observed_id",
        "partner_offer_states",
        ["offer_id", "observed_at", "id"],
    )
    op.create_index(
        "ix_offer_states_observed_id", "partner_offer_states", ["observed_at", "id"]
    )
    op.create_index(
        "ix_price_list_runs_cleanup",
        "price_list_sync_runs",
        ["status", "finished_at", "id"],
    )


def downgrade():
    """Drops only new technical fields and indexes."""
    for name, table in (
        ("ix_price_list_runs_cleanup", "price_list_sync_runs"),
        ("ix_offer_states_observed_id", "partner_offer_states"),
        ("ix_offer_states_offer_observed_id", "partner_offer_states"),
        ("ix_partner_offers_list_id", "partner_offers"),
    ):
        op.drop_index(name, table_name=table)
    op.drop_column("price_list_sync_items", "quarantined")
