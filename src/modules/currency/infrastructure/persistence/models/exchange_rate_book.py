from datetime import date, datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ExchangeRateBookModel(TenantBase):
    """Хранит книгу NBU отдельными колонками в схеме текущего тенанта."""

    __tablename__ = "currency_exchange_rate_books"
    __table_args__ = (
        sa.CheckConstraint("source = 'nbu'", name="ck_currency_book_nbu"),
        sa.CheckConstraint(
            "checked_at >= request_started_at", name="ck_currency_book_check_time"
        ),
    )
    source: Mapped[str] = mapped_column(sa.String(3), primary_key=True)
    snapshot_id: Mapped[UUID] = mapped_column(sa.Uuid, nullable=False)
    effective_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    request_started_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    checked_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
