"""Справочник внешних источников поставщиков."""

from alembic import op
import sqlalchemy as sa

revision = "0024_supplier_sources"
down_revision = "0023_inventory_stock_serials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт tenant-карточки и принадлежащие им режимы исполнения."""
    op.create_table(
        "supplier_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("supplier_model_key", sa.Text(), nullable=False),
        sa.Column("supplier_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("external_warehouse_code", sa.Text(collation="C"), nullable=True),
        sa.Column("default_lead_time_seconds", sa.BigInteger(), nullable=False),
        sa.Column("stock_ttl_seconds", sa.BigInteger(), nullable=False),
        sa.Column("stale_behavior", sa.Text(), nullable=False),
        sa.Column("missing_sku_behavior", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_supplier_sources"),
        sa.CheckConstraint(
            "supplier_model_key IN ('crm.company', 'crm.contact')",
            name="ck_supplier_sources_supplier_model_key",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name="ck_supplier_sources_name"
        ),
        sa.CheckConstraint(
            "external_warehouse_code IS NULL OR char_length(btrim(external_warehouse_code)) > 0",
            name="ck_supplier_sources_external_code",
        ),
        sa.CheckConstraint(
            "default_lead_time_seconds >= 0 AND default_lead_time_seconds <= 86399999999999",
            name="ck_supplier_sources_lead_time",
        ),
        sa.CheckConstraint(
            "stock_ttl_seconds > 0 AND stock_ttl_seconds <= 86399999999999",
            name="ck_supplier_sources_ttl",
        ),
        sa.CheckConstraint(
            "stale_behavior IN ('MARK_UNKNOWN', 'BLOCK_AUTOMATIC_SALE')",
            name="ck_supplier_sources_stale",
        ),
        sa.CheckConstraint(
            "missing_sku_behavior IN ('KEEP_LAST', 'MARK_UNKNOWN')",
            name="ck_supplier_sources_missing",
        ),
    )
    op.create_index(
        "ix_supplier_sources_supplier",
        "supplier_sources",
        ["supplier_model_key", "supplier_id"],
    )
    op.create_index("ix_supplier_sources_name_id", "supplier_sources", ["name", "id"])
    op.create_table(
        "supplier_source_fulfillment_modes",
        sa.Column("supplier_source_id", sa.UUID(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint(
            "supplier_source_id", "mode", name="pk_supplier_source_fulfillment_modes"
        ),
        sa.ForeignKeyConstraint(
            ["supplier_source_id"],
            ["supplier_sources.id"],
            name="fk_supplier_source_modes_source",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "mode IN ('DROPSHIP', 'PURCHASE_TO_WAREHOUSE')",
            name="ck_supplier_source_modes_mode",
        ),
    )


def downgrade() -> None:
    """Удаляет режимы и карточки, не затрагивая CRM."""
    op.drop_table("supplier_source_fulfillment_modes")
    op.drop_table("supplier_sources")
