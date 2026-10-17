from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ExchangeRateQuoteModel(TenantBase):
    """Хранит внутренние котировки книги, без отдельного доменного репозитория."""

    __tablename__ = "currency_exchange_rate_quotes"
    __table_args__ = (
        sa.CheckConstraint("target_currency = 'UAH'", name="ck_currency_quote_target"),
        sa.CheckConstraint(
            "source_currency <> 'UAH'", name="ck_currency_quote_foreign"
        ),
        sa.CheckConstraint("rate > 0", name="ck_currency_quote_positive"),
    )
    book_source: Mapped[str] = mapped_column(
        sa.String(3),
        sa.ForeignKey("tenant.currency_exchange_rate_books.source", ondelete="CASCADE"),
        primary_key=True,
    )
    source_currency: Mapped[str] = mapped_column(sa.String(3), primary_key=True)
    target_currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(sa.Numeric(38, 18), nullable=False)
