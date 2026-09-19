"""Add partner purchase price lists, offers and synchronization history."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_partner_price_lists"
down_revision = "0003_identity_cloud_access"
branch_labels = None
depends_on = None


def _audit_columns():
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
    ]


def upgrade():
    op.create_table(
        "price_lists",
        *_audit_columns(),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("source_format", sa.String(16), nullable=False),
        sa.Column("source_preset", sa.String(64), nullable=True),
        sa.Column("source_url_secret", sa.Text(), nullable=False),
        sa.Column("source_url_display", sa.String(2048), nullable=False),
        sa.Column(
            "source_config", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "mapping_config", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column("mapping_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cron_expression", sa.String(128), nullable=True),
        sa.Column(
            "timezone", sa.String(64), nullable=False, server_default="Europe/Kyiv"
        ),
        sa.Column(
            "new_item_policy", sa.String(32), nullable=False, server_default="create"
        ),
        sa.Column(
            "missing_item_policy",
            sa.String(32),
            nullable=False,
            server_default="mark_out_of_stock",
        ),
        sa.Column(
            "missing_threshold", sa.Integer(), nullable=False, server_default="2"
        ),
        sa.Column(
            "schedule_revision", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_run_id", sa.UUID(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('draft','ready','active','paused','invalid')",
            name="ck_price_lists_status",
        ),
        sa.CheckConstraint(
            "source_format IN ('xml','yaml','xlsx')",
            name="ck_price_lists_source_format",
        ),
        sa.CheckConstraint(
            "new_item_policy IN ('create','quarantine','ignore')",
            name="ck_price_lists_new_policy",
        ),
        sa.CheckConstraint(
            "missing_item_policy IN "
            "('mark_out_of_stock','mark_missing','keep_last','archive')",
            name="ck_price_lists_missing_policy",
        ),
        sa.CheckConstraint("missing_threshold >= 1", name="ck_price_lists_threshold"),
    )
    op.create_index(
        "ix_price_lists_status_next_sync", "price_lists", ["status", "next_sync_at"]
    )
    op.create_table(
        "partner_offers",
        *_audit_columns(),
        sa.Column("price_list_id", sa.UUID(), nullable=False),
        sa.Column("sku", sa.String(255), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column(
            "lifecycle_status", sa.String(16), nullable=False, server_default="active"
        ),
        sa.Column("current_state_id", sa.UUID(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("missing_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "consecutive_missing_runs", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.ForeignKeyConstraint(
            ["price_list_id"], ["price_lists.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "price_list_id", "external_id", name="uq_partner_offer_external_id"
        ),
    )
    op.create_index("ix_partner_offers_price_list", "partner_offers", ["price_list_id"])
    op.create_index(
        "ix_partner_offers_search", "partner_offers", ["title", "sku", "external_id"]
    )
    op.execute(
        "CREATE INDEX ix_partner_offers_search_document ON partner_offers "
        "USING gin (to_tsvector('simple', coalesce(title,'') || ' ' || "
        "coalesce(sku,'') || ' ' || coalesce(external_id,'')))"
    )
    op.create_table(
        "price_list_sync_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("price_list_id", sa.UUID(), nullable=False),
        sa.Column("scheduled_job_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("trigger", sa.String(16), nullable=False),
        sa.Column("planned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_checksum", sa.String(64), nullable=True),
        sa.Column("counters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["price_list_id"], ["price_lists.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "price_list_id", "scheduled_job_id", name="uq_price_list_run_job"
        ),
        sa.CheckConstraint(
            "status IN ('queued','downloading','parsing','applying',"
            "'succeeded','partial','failed','skipped')",
            name="ck_price_list_runs_status",
        ),
        sa.CheckConstraint(
            "trigger IN ('initial','cron','manual','retry')",
            name="ck_price_list_runs_trigger",
        ),
    )
    op.create_index(
        "ix_price_list_runs_list_started",
        "price_list_sync_runs",
        ["price_list_id", "started_at"],
    )
    op.create_table(
        "partner_offer_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("offer_id", sa.UUID(), nullable=False),
        sa.Column("sync_run_id", sa.UUID(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purchase_price", sa.Numeric(19, 4), nullable=False),
        sa.Column("rrp", sa.Numeric(19, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("availability", sa.String(16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("value_hash", sa.String(64), nullable=False),
        sa.Column("change_reason", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(
            ["offer_id"], ["partner_offers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sync_run_id"], ["price_list_sync_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("purchase_price >= 0", name="ck_offer_state_price"),
        sa.CheckConstraint("rrp IS NULL OR rrp >= 0", name="ck_offer_state_rrp"),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity >= 0", name="ck_offer_state_quantity"
        ),
        sa.CheckConstraint(
            "availability IN ('in_stock','out_of_stock','unknown')",
            name="ck_offer_state_availability",
        ),
        sa.CheckConstraint(
            "quantity IS NULL OR "
            "(quantity = 0 AND availability = 'out_of_stock') OR "
            "(quantity > 0 AND availability = 'in_stock')",
            name="ck_offer_state_quantity_availability",
        ),
    )
    op.create_index(
        "ix_offer_states_offer_observed",
        "partner_offer_states",
        ["offer_id", sa.text("observed_at DESC")],
    )
    op.create_index("ix_offer_states_run", "partner_offer_states", ["sync_run_id"])
    op.create_index("ix_offer_states_observed", "partner_offer_states", ["observed_at"])
    op.create_foreign_key(
        "fk_partner_offers_current_state",
        "partner_offers",
        "partner_offer_states",
        ["current_state_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_price_lists_last_sync_run",
        "price_lists",
        "price_list_sync_runs",
        ["last_sync_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "price_list_sync_items",
        sa.Column("sync_run_id", sa.UUID(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("sku", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("purchase_price", sa.Numeric(19, 4), nullable=True),
        sa.Column("rrp", sa.Numeric(19, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("availability", sa.String(16), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("value_hash", sa.String(64), nullable=True),
        sa.Column(
            "normalized_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "validation_errors", postgresql.JSONB(), nullable=False, server_default="[]"
        ),
        sa.ForeignKeyConstraint(
            ["sync_run_id"], ["price_list_sync_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("sync_run_id", "row_number"),
        sa.UniqueConstraint(
            "sync_run_id", "external_id", name="uq_sync_item_external_id"
        ),
    )


def downgrade():
    op.drop_table("price_list_sync_items")
    op.drop_constraint(
        "fk_price_lists_last_sync_run", "price_lists", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_partner_offers_current_state", "partner_offers", type_="foreignkey"
    )
    op.drop_index("ix_offer_states_observed", table_name="partner_offer_states")
    op.drop_index("ix_offer_states_run", table_name="partner_offer_states")
    op.drop_index("ix_offer_states_offer_observed", table_name="partner_offer_states")
    op.drop_table("partner_offer_states")
    op.drop_index("ix_price_list_runs_list_started", table_name="price_list_sync_runs")
    op.drop_table("price_list_sync_runs")
    op.drop_index("ix_partner_offers_search_document", table_name="partner_offers")
    op.drop_index("ix_partner_offers_search", table_name="partner_offers")
    op.drop_index("ix_partner_offers_price_list", table_name="partner_offers")
    op.drop_table("partner_offers")
    op.drop_index("ix_price_lists_status_next_sync", table_name="price_lists")
    op.drop_table("price_lists")
