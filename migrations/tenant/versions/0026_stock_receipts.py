"""Первое атомарное поступление: физический учёт и исходные стоимостные основания."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0026_stock_receipts"
down_revision = "0025_stock_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт таблицы и ограничения целостности без функций и триггеров."""
    op.create_table(
        "stock_positions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inventory_item_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("lot_id", sa.UUID(), nullable=True),
        sa.Column("serial_id", sa.UUID(), nullable=True),
        sa.Column("stock_status", sa.Text(), nullable=False),
        sa.Column("base_uom", sa.Text(), nullable=False),
        sa.Column("on_hand_qty", sa.Numeric(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stock_positions"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name="fk_stock_positions_item",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["stock_locations.id"],
            name="fk_stock_positions_location",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            ["stock_lots.id"],
            name="fk_stock_positions_lot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["serial_id"],
            ["stock_serials.id"],
            name="fk_stock_positions_serial",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "inventory_item_id",
            "location_id",
            "owner_id",
            "lot_id",
            "serial_id",
            "stock_status",
            name="uq_stock_positions_dimensions",
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint(
            "on_hand_qty >= 0 AND on_hand_qty NOT IN ('NaN'::numeric,'Infinity'::numeric) AND (serial_id IS NULL OR on_hand_qty IN (0,1))",
            name="ck_stock_positions_quantity",
        ),
        sa.CheckConstraint("version >= 0", name="ck_stock_positions_version"),
        sa.CheckConstraint(
            "stock_status IN ('SELLABLE','QUARANTINE','DAMAGED','BLOCKED')",
            name="ck_stock_positions_status",
        ),
    )
    op.create_index("ix_stock_positions_item", "stock_positions", ["inventory_item_id"])
    op.create_index(
        "uq_stock_positions_serial_positive",
        "stock_positions",
        ["serial_id"],
        unique=True,
        postgresql_where=sa.text("on_hand_qty > 0 AND serial_id IS NOT NULL"),
    )
    op.create_table(
        "stock_executions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("document_version", sa.BigInteger(), nullable=False),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("warehouse_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stock_executions"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["stock_documents.id"],
            name="fk_stock_executions_document",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name="fk_stock_executions_warehouse",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("document_version >= 0", name="ck_stock_executions_version"),
    )
    op.create_index(
        "ix_stock_executions_document",
        "stock_executions",
        ["document_id", "executed_at", "id"],
    )
    op.create_table(
        "stock_execution_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("document_line_id", sa.UUID(), nullable=False),
        sa.Column("inventory_item_id", sa.UUID(), nullable=False),
        sa.Column("base_uom", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("source_quantity", sa.Numeric(), nullable=False),
        sa.Column("source_uom", sa.Text(), nullable=False),
        sa.Column("factor_to_base", sa.Numeric(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("lot_id", sa.UUID(), nullable=True),
        sa.Column("serial_id", sa.UUID(), nullable=True),
        sa.Column("stock_status", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stock_execution_lines"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["stock_executions.id"],
            name="fk_stock_execution_lines_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_line_id"],
            ["stock_document_lines.id"],
            name="fk_stock_execution_lines_document_line",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name="fk_stock_execution_lines_item",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["stock_locations.id"],
            name="fk_stock_execution_lines_location",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            ["stock_lots.id"],
            name="fk_stock_execution_lines_lot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["serial_id"],
            ["stock_serials.id"],
            name="fk_stock_execution_lines_serial",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "execution_id", "position", name="uq_stock_execution_lines_position"
        ),
        sa.CheckConstraint(
            "quantity > 0 AND quantity NOT IN ('NaN'::numeric,'Infinity'::numeric) AND source_quantity > 0 AND source_quantity NOT IN ('NaN'::numeric,'Infinity'::numeric) AND factor_to_base > 0 AND factor_to_base NOT IN ('NaN'::numeric,'Infinity'::numeric) AND position >= 0",
            name="ck_stock_execution_lines_quantity",
        ),
    )
    op.create_table(
        "stock_receipt_cost_evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("total_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("basis_kind", sa.Text(), nullable=False),
        sa.Column("source_system", sa.Text(), nullable=True),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_stock_receipt_cost_evidence"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["stock_executions.id"],
            name="fk_receipt_cost_execution",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "total_amount >= 0 AND total_amount != 'NaN'::numeric",
            name="ck_receipt_cost_amount",
        ),
        sa.CheckConstraint(
            "basis_kind IN ('MANUAL','EXTERNAL')", name="ck_receipt_cost_basis"
        ),
    )
    op.create_index(
        "ix_receipt_cost_execution", "stock_receipt_cost_evidence", ["execution_id"]
    )
    op.create_table(
        "stock_receipt_cost_allocations",
        sa.Column("evidence_id", sa.UUID(), nullable=False),
        sa.Column("execution_line_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.PrimaryKeyConstraint(
            "evidence_id", "execution_line_id", name="pk_stock_receipt_cost_allocations"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["stock_receipt_cost_evidence.id"],
            name="fk_receipt_allocation_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_line_id"],
            ["stock_execution_lines.id"],
            name="fk_receipt_allocation_line",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "amount >= 0 AND amount != 'NaN'::numeric",
            name="ck_receipt_allocation_amount",
        ),
    )
    op.create_table(
        "stock_postings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reversal_of_id", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_stock_postings"),
        sa.UniqueConstraint("execution_id", name="uq_stock_postings_execution"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["stock_executions.id"],
            name="fk_stock_postings_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reversal_of_id"],
            ["stock_postings.id"],
            name="fk_stock_postings_reversal",
            ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "stock_ledger_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("posting_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.UUID(), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(), nullable=False),
        sa.Column("base_uom", sa.Text(), nullable=False),
        sa.Column("source_quantity", sa.Numeric(), nullable=False),
        sa.Column("source_uom", sa.Text(), nullable=False),
        sa.Column("factor_to_base", sa.Numeric(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stock_ledger_entries"),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["stock_postings.id"],
            name="fk_ledger_posting",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["stock_positions.id"],
            name="fk_ledger_position",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "posting_id", "position_id", name="uq_ledger_posting_position"
        ),
        sa.UniqueConstraint("posting_id", "position", name="uq_ledger_ordinal"),
        sa.CheckConstraint(
            "quantity_delta NOT IN (0,'NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND source_quantity > 0 AND source_quantity NOT IN ('NaN'::numeric,'Infinity'::numeric) AND factor_to_base > 0 AND factor_to_base NOT IN ('NaN'::numeric,'Infinity'::numeric)",
            name="ck_ledger_quantities",
        ),
    )
    op.create_index("ix_ledger_position", "stock_ledger_entries", ["position_id"])
    op.create_table(
        "stock_execution_ledger_links",
        sa.Column("execution_line_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("ledger_entry_id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint(
            "execution_line_id", "role", name="pk_stock_execution_ledger_links"
        ),
        sa.ForeignKeyConstraint(
            ["execution_line_id"],
            ["stock_execution_lines.id"],
            name="fk_execution_link_line",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ledger_entry_id"],
            ["stock_ledger_entries.id"],
            name="fk_execution_link_entry",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "role IN ('SOURCE','DESTINATION')", name="ck_execution_link_role"
        ),
    )
    op.create_table(
        "stock_receipt_posting_requests",
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=True),
        sa.Column("posting_id", sa.UUID(), nullable=True),
        sa.Column("result", JSONB(none_as_null=True), nullable=True),
        sa.PrimaryKeyConstraint("key", name="pk_stock_receipt_posting_requests"),
        sa.UniqueConstraint("execution_id", name="uq_receipt_request_execution"),
        sa.UniqueConstraint("posting_id", name="uq_receipt_request_posting"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["stock_executions.id"],
            name="fk_receipt_request_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["stock_postings.id"],
            name="fk_receipt_request_posting",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(execution_id IS NULL AND posting_id IS NULL AND result IS NULL) OR (execution_id IS NOT NULL AND posting_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_receipt_request_result",
        ),
    )


def downgrade() -> None:
    """Удаляет только таблицы этого среза в порядке внешних ссылок."""
    op.drop_table("stock_receipt_posting_requests")
    op.drop_table("stock_execution_ledger_links")
    op.drop_table("stock_ledger_entries")
    op.drop_table("stock_postings")
    op.drop_table("stock_receipt_cost_allocations")
    op.drop_table("stock_receipt_cost_evidence")
    op.drop_table("stock_execution_lines")
    op.drop_table("stock_executions")
    op.drop_table("stock_positions")
