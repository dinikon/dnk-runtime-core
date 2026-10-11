from collections.abc import Mapping, Sequence
from typing import Any
from src.modules.currency.domain.aggregate import ExchangeRateBook
from src.modules.currency.domain.value_object.quote import ExchangeRateQuoteVO
from src.modules.currency.domain.value_object.snapshot_id import (
    ExchangeRateSnapshotIdVO,
)
from src.modules.shared.domain.value_object.currency import CurrencyVO


class ExchangeRateBookMapper:
    """Преобразует целый агрегат и SQL-представление без инвариантов или I/O."""

    @staticmethod
    def to_domain(
        row: Mapping[str, Any], quote_rows: Sequence[Mapping[str, Any]]
    ) -> ExchangeRateBook:
        """Восстанавливает книгу через фабрику с принадлежащими ей котировками."""
        return ExchangeRateBook.restore(
            snapshot_id=ExchangeRateSnapshotIdVO.from_value(row["snapshot_id"]),
            effective_date=row["effective_date"],
            request_started_at=row["request_started_at"],
            checked_at=row["checked_at"],
            quotes=tuple(
                ExchangeRateQuoteVO(CurrencyVO(item["source_currency"]), item["rate"])
                for item in quote_rows
            ),
        )

    @staticmethod
    def to_book_values(book: ExchangeRateBook) -> dict[str, Any]:
        """Извлекает колонки состояния книги для INSERT/UPDATE."""
        return {
            "source": "nbu",
            "snapshot_id": book.snapshot_id.uuid,
            "effective_date": book.effective_date,
            "request_started_at": book.request_started_at,
            "checked_at": book.checked_at,
        }

    @staticmethod
    def to_quote_values(book: ExchangeRateBook) -> list[dict[str, Any]]:
        """Извлекает отдельные колонки всего набора котировок."""
        return [
            {
                "book_source": "nbu",
                "source_currency": quote.currency.value,
                "target_currency": "UAH",
                "rate": quote.rate,
            }
            for quote in book.quotes
        ]
