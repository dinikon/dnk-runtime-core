"""Реквизиты и точные основания RETURN с отдельными журналами идемпотентности."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0033_stock_returns"
down_revision = "0032_stock_status_changes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет хранение операции и ограничения целостности без бизнес-функций или триггеров."""
    op.drop_constraint("ck_stock_documents_operation", "stock_documents", type_="check")
    op.create_check_constraint(
        "ck_stock_documents_operation",
        "stock_documents",
        "operation_type IN ('RECEIPT','ISSUE','INTERNAL_MOVE','ADJUSTMENT','WRITE_OFF','STATUS_CHANGE','RETURN')",
    )
    op.create_table(
        "stock_document_returns",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("origin_execution_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["origin_execution_id"],
            ["stock_executions.id"],
            name="fk_document_return_origin",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("document_id", name="pk_stock_document_returns"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["stock_documents.id"],
            name="fk_document_return_root",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "direction IN ('FROM_RECIPIENT','TO_SUPPLIER')",
            name="ck_document_return_direction",
        ),
    )
    op.create_index(
        "ix_document_returns_origin", "stock_document_returns", ["origin_execution_id"]
    )
    op.create_table(
        "stock_document_return_lines",
        sa.Column("document_line_id", sa.UUID(), nullable=False),
        sa.Column("origin_execution_line_id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint(
            "document_line_id", name="pk_stock_document_return_lines"
        ),
        sa.ForeignKeyConstraint(
            ["document_line_id"],
            ["stock_document_lines.id"],
            name="fk_document_return_line_root",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["origin_execution_line_id"],
            ["stock_execution_lines.id"],
            name="fk_document_return_line_origin",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_document_return_lines_origin",
        "stock_document_return_lines",
        ["origin_execution_line_id"],
    )
    op.create_table(
        "stock_execution_returns",
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("origin_execution_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["origin_execution_id"],
            ["stock_executions.id"],
            name="fk_execution_return_origin",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("execution_id", name="pk_stock_execution_returns"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["stock_executions.id"],
            name="fk_execution_return_root",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "direction IN ('FROM_RECIPIENT','TO_SUPPLIER')",
            name="ck_execution_return_direction",
        ),
    )
    op.create_index(
        "ix_execution_returns_origin",
        "stock_execution_returns",
        ["origin_execution_id"],
    )
    op.create_table(
        "stock_execution_return_lines",
        sa.Column("execution_line_id", sa.UUID(), nullable=False),
        sa.Column("origin_execution_line_id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint(
            "execution_line_id", name="pk_stock_execution_return_lines"
        ),
        sa.ForeignKeyConstraint(
            ["execution_line_id"],
            ["stock_execution_lines.id"],
            name="fk_execution_return_line_root",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["origin_execution_line_id"],
            ["stock_execution_lines.id"],
            name="fk_execution_return_line_origin",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_execution_return_lines_origin",
        "stock_execution_return_lines",
        ["origin_execution_line_id"],
    )
    op.create_table(
        "stock_return_creation_requests",
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("result", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "actor_id",
            "idempotency_key",
            name="pk_stock_return_creation_requests",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["stock_documents.id"],
            name="fk_stock_return_creation_requests_document",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(document_id IS NULL AND result IS NULL) OR (document_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_stock_return_creation_requests_result",
        ),
    )
    op.create_table(
        "stock_return_posting_requests",
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=True),
        sa.Column("posting_id", sa.UUID(), nullable=True),
        sa.Column("result", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.PrimaryKeyConstraint("key", name="pk_stock_return_posting_requests"),
        sa.UniqueConstraint("execution_id", name="uq_return_request_execution"),
        sa.UniqueConstraint("posting_id", name="uq_return_request_posting"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["stock_executions.id"],
            name="fk_return_request_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["stock_postings.id"],
            name="fk_return_request_posting",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(execution_id IS NULL AND posting_id IS NULL AND result IS NULL) OR (execution_id IS NOT NULL AND posting_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_return_request_result",
        ),
    )


def downgrade() -> None:
    """Удаляет новый срез; существующие RETURN предварительно запрещают downgrade."""
    op.drop_constraint("ck_stock_documents_operation", "stock_documents", type_="check")
    op.create_check_constraint(
        "ck_stock_documents_operation",
        "stock_documents",
        "operation_type IN ('RECEIPT','ISSUE','INTERNAL_MOVE','ADJUSTMENT','WRITE_OFF','STATUS_CHANGE')",
    )
    op.drop_table("stock_return_posting_requests")
    op.drop_table("stock_return_creation_requests")

    op.drop_table("stock_execution_return_lines")
    op.drop_table("stock_document_return_lines")
    op.drop_table("stock_execution_returns")
    op.drop_table("stock_document_returns")
