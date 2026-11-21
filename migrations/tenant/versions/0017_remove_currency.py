"""Удаление tenant-книги курсов после отключения модуля Currency.

Перед upgrade завершите запуски старой команды currency refresh. Downgrade
восстанавливает только пустую структуру; котировки доступны из резервной копии.
"""

from alembic import op
import sqlalchemy as sa

revision = "0017_remove_currency"
down_revision = "0016_channels_connections_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Удаляет котировки и книгу текущего tenant без каскадного удаления."""
    op.drop_table("currency_exchange_rate_quotes")
    op.drop_table("currency_exchange_rate_books")


def downgrade() -> None:
    """Восстанавливает пустые исторические таблицы и их ограничения."""
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
        sa.Column("book_source", sa.String(3), primary_key=True),
        sa.Column("source_currency", sa.String(3), primary_key=True),
        sa.Column("target_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(38, 18), nullable=False),
        sa.ForeignKeyConstraint(
            ["book_source"], ["currency_exchange_rate_books.source"], ondelete="CASCADE"
        ),
        sa.CheckConstraint("target_currency = 'UAH'", name="ck_currency_quote_target"),
        sa.CheckConstraint(
            "source_currency <> 'UAH'", name="ck_currency_quote_foreign"
        ),
        sa.CheckConstraint("rate > 0", name="ck_currency_quote_positive"),
    )
