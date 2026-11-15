"""Отдельные журналы идемпотентности создания и проведения ручного INTERNAL_MOVE."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0030_internal_moves"
down_revision = "0029_stock_issues"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет второй адрес маршрута и технические журналы ручного перемещения."""
    op.add_column(
        "stock_execution_lines",
        sa.Column("destination_location_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_execution_lines_destination_location",
        "stock_execution_lines",
        ["destination_location_id"],
    )
    op.create_foreign_key(
        "fk_execution_lines_destination_location",
        "stock_execution_lines",
        "stock_locations",
        ["destination_location_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "stock_internal_move_creation_requests",
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("result", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "actor_id",
            "idempotency_key",
            name="pk_stock_internal_move_creation_requests",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["stock_documents.id"],
            name="fk_stock_internal_move_creation_requests_document",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(document_id IS NULL AND result IS NULL) OR (document_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_stock_internal_move_creation_requests_result",
        ),
    )
    op.create_table(
        "stock_internal_move_posting_requests",
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=True),
        sa.Column("posting_id", sa.UUID(), nullable=True),
        sa.Column("result", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.PrimaryKeyConstraint("key", name="pk_stock_internal_move_posting_requests"),
        sa.UniqueConstraint("execution_id", name="uq_internal_move_request_execution"),
        sa.UniqueConstraint("posting_id", name="uq_internal_move_request_posting"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["stock_executions.id"],
            name="fk_internal_move_request_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["stock_postings.id"],
            name="fk_internal_move_request_posting",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(execution_id IS NULL AND posting_id IS NULL AND result IS NULL) OR (execution_id IS NOT NULL AND posting_id IS NOT NULL AND result IS NOT NULL)",
            name="ck_internal_move_request_result",
        ),
    )


def downgrade() -> None:
    """Удаляет новые журналы и второй адрес фактического маршрута."""
    op.drop_table("stock_internal_move_posting_requests")
    op.drop_table("stock_internal_move_creation_requests")

    op.drop_constraint(
        "fk_execution_lines_destination_location",
        "stock_execution_lines",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_execution_lines_destination_location", table_name="stock_execution_lines"
    )
    op.drop_column("stock_execution_lines", "destination_location_id")
