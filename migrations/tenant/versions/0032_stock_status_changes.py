"""Реквизиты плана и факта STATUS_CHANGE, новое состояние маршрута и журналы ключей."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0032_stock_status_changes"
down_revision = "0031_stock_write_offs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет хранение операции и ограничения целостности без бизнес-функций или триггеров."""
    op.add_column(
        "stock_execution_lines",
        sa.Column("destination_stock_status", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_execution_lines_destination_stock_status",
        "stock_execution_lines",
        "destination_stock_status IS NULL OR destination_stock_status IN ('SELLABLE','QUARANTINE','DAMAGED','BLOCKED')",
    )
    op.drop_constraint("ck_stock_documents_operation", "stock_documents", type_="check")
    op.create_check_constraint(
        "ck_stock_documents_operation",
        "stock_documents",
        "operation_type IN ('RECEIPT','ISSUE','INTERNAL_MOVE','ADJUSTMENT','WRITE_OFF','STATUS_CHANGE')",
    )
    op.create_table(
        "stock_document_status_changes",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("target_status", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("document_id", name="pk_stock_document_status_changes"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["stock_documents.id"],
            name="fk_document_status_change_root",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "target_status IN ('SELLABLE','QUARANTINE','DAMAGED','BLOCKED')",
            name="ck_document_status_change_target",
        ),
    )
    op.create_table(
        "stock_execution_status_changes",
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("target_status", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint(
            "execution_id", name="pk_stock_execution_status_changes"
        ),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["stock_executions.id"],
            name="fk_execution_status_change_root",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "target_status IN ('SELLABLE','QUARANTINE','DAMAGED','BLOCKED')",
            name="ck_execution_status_change_target",
        ),
    )
    op.create_table(
        "stock_status_change_creation_requests",
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("result", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "actor_id",
            "idempotency_key",
            name="pk_stock_status_change_creation_requests",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["stock_documents.id"],
            name="fk_stock_status_change_creation_requests_document",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(document_id IS NULL AND result IS NULL) OR (document_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_stock_status_change_creation_requests_result",
        ),
    )
    op.create_table(
        "stock_status_change_posting_requests",
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=True),
        sa.Column("posting_id", sa.UUID(), nullable=True),
        sa.Column("result", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.PrimaryKeyConstraint("key", name="pk_stock_status_change_posting_requests"),
        sa.UniqueConstraint("execution_id", name="uq_status_change_request_execution"),
        sa.UniqueConstraint("posting_id", name="uq_status_change_request_posting"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["stock_executions.id"],
            name="fk_status_change_request_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["stock_postings.id"],
            name="fk_status_change_request_posting",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(execution_id IS NULL AND posting_id IS NULL AND result IS NULL) OR (execution_id IS NOT NULL AND posting_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_status_change_request_result",
        ),
    )


def downgrade() -> None:
    """Удаляет новый срез; существующие STATUS_CHANGE предварительно запрещают downgrade."""
    op.drop_constraint("ck_stock_documents_operation", "stock_documents", type_="check")
    op.create_check_constraint(
        "ck_stock_documents_operation",
        "stock_documents",
        "operation_type IN ('RECEIPT','ISSUE','INTERNAL_MOVE','ADJUSTMENT','WRITE_OFF')",
    )
    op.drop_table("stock_status_change_posting_requests")
    op.drop_table("stock_status_change_creation_requests")

    op.drop_table("stock_execution_status_changes")
    op.drop_table("stock_document_status_changes")
    op.drop_constraint(
        "ck_execution_lines_destination_stock_status",
        "stock_execution_lines",
        type_="check",
    )
    op.drop_column("stock_execution_lines", "destination_stock_status")
