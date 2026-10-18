"""Книга NBU в каждой tenant-схеме и атомарный набор котировок, без сетевых обращений."""

from alembic import op
import sqlalchemy as sa

revision = "0024_currency_exchange_rates"
down_revision = "0023_catalog_item"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт пустое хранилище для первой ручной загрузки NBU."""
    op.create_table(
        "currency_exchange_rate_books",
        sa.Column("source", sa.String(3), primary_key=True),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("request_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source = 'nbu'", name="ck_currency_book_nbu"),
        sa.CheckConstraint(
            "checked_at >= request_started_at", name="ck_currency_book_check_time"
        ),
    )
    op.create_table(
        "currency_exchange_rate_quotes",
        sa.Column(
            "book_source",
            sa.String(3),
            sa.ForeignKey("currency_exchange_rate_books.source", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("source_currency", sa.String(3), primary_key=True),
        sa.Column("target_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(38, 18), nullable=False),
        sa.CheckConstraint("target_currency = 'UAH'", name="ck_currency_quote_target"),
        sa.CheckConstraint(
            "source_currency <> 'UAH'", name="ck_currency_quote_foreign"
        ),
        sa.CheckConstraint("rate > 0", name="ck_currency_quote_positive"),
    )


def downgrade() -> None:
    """Удаляет только таблицы валютной книги."""
    op.drop_table("currency_exchange_rate_quotes")
    op.drop_table("currency_exchange_rate_books")
