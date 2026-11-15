"""Черновики складских документов, строки и атомарная идемпотентность создания."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0025_stock_documents"
down_revision = "0024_supplier_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт только таблицы, индексы и декларативные ограничения целостности."""
    op.create_table(
        "stock_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("warehouse_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source_system", sa.Text(), nullable=True),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("source_version", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stock_documents"),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name="fk_stock_documents_warehouse",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "operation_type IN ('RECEIPT','ISSUE','INTERNAL_MOVE','ADJUSTMENT')",
            name="ck_stock_documents_operation",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','CONFIRMED','PARTIALLY_EXECUTED','COMPLETED','CANCELLED')",
            name="ck_stock_documents_status",
        ),
        sa.CheckConstraint("version >= 0", name="ck_stock_documents_version"),
        sa.CheckConstraint(
            "(source_system IS NULL AND source_reference IS NULL AND source_version IS NULL) OR (source_system IS NOT NULL AND source_reference IS NOT NULL AND (source_version IS NULL OR source_version >= 0))",
            name="ck_stock_documents_source",
        ),
    )
    op.create_index(
        "ix_stock_documents_created", "stock_documents", ["created_at", "id"]
    )
    op.create_index("ix_stock_documents_owner", "stock_documents", ["owner_id"])
    op.create_index("ix_stock_documents_warehouse", "stock_documents", ["warehouse_id"])
    op.create_table(
        "stock_document_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("inventory_item_id", sa.UUID(), nullable=False),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column("base_uom", sa.Text(), nullable=False),
        sa.Column("planned_qty", sa.Numeric(), nullable=False),
        sa.Column("source_quantity", sa.Numeric(), nullable=False),
        sa.Column("source_uom", sa.Text(), nullable=False),
        sa.Column("factor_to_base", sa.Numeric(), nullable=False),
        sa.Column("executed_qty", sa.Numeric(), nullable=False),
        sa.Column("source_system", sa.Text(), nullable=True),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_stock_document_lines"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["stock_documents.id"],
            name="fk_stock_document_lines_document",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name="fk_stock_document_lines_item",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "document_id", "position", name="uq_stock_document_lines_position"
        ),
        sa.CheckConstraint("position >= 0", name="ck_stock_document_lines_position"),
        sa.CheckConstraint(
            "planned_qty > 0 AND planned_qty NOT IN ('NaN'::numeric,'Infinity'::numeric) AND source_quantity > 0 AND source_quantity NOT IN ('NaN'::numeric,'Infinity'::numeric) AND factor_to_base > 0 AND factor_to_base NOT IN ('NaN'::numeric,'Infinity'::numeric) AND executed_qty >= 0 AND executed_qty <= planned_qty AND executed_qty != 'NaN'::numeric",
            name="ck_stock_document_lines_quantities",
        ),
        sa.CheckConstraint(
            "(source_system IS NULL AND source_reference IS NULL) OR (source_system IS NOT NULL AND source_reference IS NOT NULL)",
            name="ck_stock_document_lines_source",
        ),
    )
    op.create_index(
        "ix_stock_document_lines_item", "stock_document_lines", ["inventory_item_id"]
    )
    op.create_table(
        "stock_document_creation_requests",
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("result", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "actor_id", "idempotency_key", name="pk_stock_document_creation_requests"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["stock_documents.id"],
            name="fk_stock_document_creation_requests_document",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(document_id IS NULL AND result IS NULL) OR (document_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_stock_document_creation_requests_result",
        ),
    )


def downgrade() -> None:
    """Удаляет только таблицы этого среза в порядке зависимостей."""
    op.drop_table("stock_document_creation_requests")
    op.drop_table("stock_document_lines")
    op.drop_table("stock_documents")
