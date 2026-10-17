from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.modules.currency.domain.error import (
    InvalidExchangeRateSnapshotError,
    OlderExchangeRateSnapshotError,
)
from src.modules.currency.domain.value_object.quote import ExchangeRateQuoteVO
from src.modules.currency.domain.value_object.snapshot_id import (
    ExchangeRateSnapshotIdVO,
)


@dataclass(slots=True)
class ExchangeRateBook:
    """Глобальная книга NBU, атомарно управляющая всем набором котировок."""

    snapshot_id: ExchangeRateSnapshotIdVO
    effective_date: date
    request_started_at: datetime
    checked_at: datetime
    quotes: tuple[ExchangeRateQuoteVO, ...]

    @classmethod
    def create(
        cls,
        *,
        effective_date: date,
        request_started_at: datetime,
        checked_at: datetime,
        quotes: tuple[ExchangeRateQuoteVO, ...],
    ) -> "ExchangeRateBook":
        """Создаёт первый согласованный снимок книги."""
        cls._validate(effective_date, request_started_at, checked_at, quotes)
        return cls(
            ExchangeRateSnapshotIdVO.generate(),
            effective_date,
            request_started_at,
            checked_at,
            cls._ordered(quotes),
        )

    @classmethod
    def restore(
        cls,
        *,
        snapshot_id: ExchangeRateSnapshotIdVO,
        effective_date: date,
        request_started_at: datetime,
        checked_at: datetime,
        quotes: tuple[ExchangeRateQuoteVO, ...],
    ) -> "ExchangeRateBook":
        """Восстанавливает книгу без генерации нового снимка."""
        cls._validate(effective_date, request_started_at, checked_at, quotes)
        if not isinstance(snapshot_id, ExchangeRateSnapshotIdVO):
            raise InvalidExchangeRateSnapshotError("Snapshot identifier is required.")
        return cls(
            snapshot_id,
            effective_date,
            request_started_at,
            checked_at,
            cls._ordered(quotes),
        )

    def refresh(
        self,
        *,
        effective_date: date,
        request_started_at: datetime,
        checked_at: datetime,
        quotes: tuple[ExchangeRateQuoteVO, ...],
    ) -> None:
        """Обновляет снимок или подтверждает прежний, отклоняя запоздавшие проверки."""
        self._validate(effective_date, request_started_at, checked_at, quotes)
        ordered = self._ordered(quotes)
        if (
            effective_date < self.effective_date
            or request_started_at < self.request_started_at
            or checked_at < self.checked_at
        ):
            raise OlderExchangeRateSnapshotError("A newer check is already published.")
        changed = effective_date != self.effective_date or ordered != self.quotes
        if request_started_at == self.request_started_at:
            if changed or checked_at != self.checked_at:
                raise OlderExchangeRateSnapshotError(
                    "Conflicting result of the same check."
                )
            return
        if changed:
            self.snapshot_id = ExchangeRateSnapshotIdVO.generate()
        self.effective_date = effective_date
        self.request_started_at = request_started_at
        self.checked_at = checked_at
        self.quotes = ordered

    @staticmethod
    def _ordered(
        quotes: tuple[ExchangeRateQuoteVO, ...],
    ) -> tuple[ExchangeRateQuoteVO, ...]:
        """Сравнивает состав снимков независимо от порядка ответа источника."""
        return tuple(sorted(quotes, key=lambda quote: quote.currency.value))

    @staticmethod
    def _validate(
        effective_date: date,
        started: datetime,
        checked: datetime,
        quotes: tuple[ExchangeRateQuoteVO, ...],
    ) -> None:
        """Проверяет инварианты книги, а не представление хранения."""
        if type(effective_date) is not date or any(
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
            for value in (started, checked)
        ):
            raise InvalidExchangeRateSnapshotError(
                "Date and aware timestamps are required."
            )
        if checked < started or not isinstance(quotes, tuple) or not quotes:
            raise InvalidExchangeRateSnapshotError(
                "Nonempty consistent snapshot is required."
            )
        if (
            effective_date != started.astimezone(ZoneInfo("Europe/Kyiv")).date()
            or effective_date != checked.astimezone(ZoneInfo("Europe/Kyiv")).date()
        ):
            raise InvalidExchangeRateSnapshotError(
                "Snapshot must belong to the checked Kyiv date."
            )
        codes: set[str] = set()
        for quote in quotes:
            if (
                not isinstance(quote, ExchangeRateQuoteVO)
                or quote.currency.value == "UAH"
                or quote.currency.value in codes
            ):
                raise InvalidExchangeRateSnapshotError(
                    "Quotes must contain unique foreign currencies."
                )
            codes.add(quote.currency.value)
