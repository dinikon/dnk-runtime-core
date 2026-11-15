"""Индексы физических остатков, фильтров фактов и обратной детализации Ledger."""

from alembic import op
import sqlalchemy as sa

revision = "0028_stock_read_side"
down_revision = "0027_drop_supplier_sourcing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет только индексы чтения; бизнес-политики остаются в коде."""
    op.create_index(
        "ix_positions_location_owner_item",
        "stock_positions",
        ["location_id", "owner_id", "inventory_item_id", "id"],
    )
    op.create_index(
        "ix_positions_owner_item",
        "stock_positions",
        ["owner_id", "inventory_item_id", "id"],
    )
    op.create_index(
        "ix_positions_lot",
        "stock_positions",
        ["lot_id", "id"],
        postgresql_where=sa.text("lot_id IS NOT NULL"),
    )
    op.create_index(
        "ix_positions_serial",
        "stock_positions",
        ["serial_id", "id"],
        postgresql_where=sa.text("serial_id IS NOT NULL"),
    )
    op.create_index("ix_executions_time", "stock_executions", ["executed_at", "id"])
    op.create_index("ix_postings_time", "stock_postings", ["posted_at", "id"])
    op.create_index(
        "ix_execution_lines_item",
        "stock_execution_lines",
        ["inventory_item_id", "execution_id"],
    )
    op.create_index(
        "ix_execution_links_entry", "stock_execution_ledger_links", ["ledger_entry_id"]
    )


def downgrade() -> None:
    """Удаляет индексы без изменения учётных данных."""
    op.drop_index("ix_execution_links_entry", table_name="stock_execution_ledger_links")
    op.drop_index("ix_execution_lines_item", table_name="stock_execution_lines")
    op.drop_index("ix_postings_time", table_name="stock_postings")
    op.drop_index("ix_executions_time", table_name="stock_executions")
    op.drop_index("ix_positions_serial", table_name="stock_positions")
    op.drop_index("ix_positions_lot", table_name="stock_positions")
    op.drop_index("ix_positions_owner_item", table_name="stock_positions")
    op.drop_index("ix_positions_location_owner_item", table_name="stock_positions")
