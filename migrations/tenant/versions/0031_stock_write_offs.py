"""Отдельные журналы идемпотентности создания и проведения ручного WRITE_OFF."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0031_stock_write_offs"
down_revision = "0030_internal_moves"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет только технические записи; существующий учёт хранит ISSUE и SOURCE."""
    op.add_column(
        "stock_documents", sa.Column("write_off_reason", sa.Text(), nullable=True)
    )
    op.add_column(
        "stock_executions", sa.Column("write_off_reason", sa.Text(), nullable=True)
    )
    op.drop_constraint("ck_stock_documents_operation", "stock_documents", type_="check")
    op.create_check_constraint(
        "ck_stock_documents_operation",
        "stock_documents",
        "operation_type IN ('RECEIPT','ISSUE','INTERNAL_MOVE','ADJUSTMENT','WRITE_OFF')",
    )
    op.create_table(
        "stock_write_off_creation_requests",
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("result", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "actor_id", "idempotency_key", name="pk_stock_write_off_creation_requests"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["stock_documents.id"],
            name="fk_stock_write_off_creation_requests_document",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(document_id IS NULL AND result IS NULL) OR (document_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_stock_write_off_creation_requests_result",
        ),
    )
    op.create_table(
        "stock_write_off_posting_requests",
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=True),
        sa.Column("posting_id", sa.UUID(), nullable=True),
        sa.Column("result", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.PrimaryKeyConstraint("key", name="pk_stock_write_off_posting_requests"),
        sa.UniqueConstraint("execution_id", name="uq_write_off_request_execution"),
        sa.UniqueConstraint("posting_id", name="uq_write_off_request_posting"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["stock_executions.id"],
            name="fk_write_off_request_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["stock_postings.id"],
            name="fk_write_off_request_posting",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(execution_id IS NULL AND posting_id IS NULL AND result IS NULL) OR (execution_id IS NOT NULL AND posting_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_write_off_request_result",
        ),
    )


def downgrade() -> None:
    """Удаляет только новые технические журналы."""
    op.drop_constraint("ck_stock_documents_operation", "stock_documents", type_="check")
    op.create_check_constraint(
        "ck_stock_documents_operation",
        "stock_documents",
        "operation_type IN ('RECEIPT','ISSUE','INTERNAL_MOVE','ADJUSTMENT')",
    )
    op.drop_table("stock_write_off_posting_requests")
    op.drop_table("stock_write_off_creation_requests")

    op.drop_column("stock_executions", "write_off_reason")
    op.drop_column("stock_documents", "write_off_reason")
