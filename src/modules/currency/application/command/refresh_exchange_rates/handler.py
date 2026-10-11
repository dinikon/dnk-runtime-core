from zoneinfo import ZoneInfo
from src.modules.currency.application.command.refresh_exchange_rates.command import (
    RefreshExchangeRatesCommand,
)
from src.modules.currency.application.command.refresh_exchange_rates.dto import (
    RefreshExchangeRatesResultDTO,
)
from src.modules.currency.application.error import (
    ExchangeRateCatalogMismatchError,
    ExchangeRateSourceError,
)
from src.modules.currency.application.port.source import ExchangeRateSourceProtocol
from src.modules.currency.application.port.catalog import (
    ExchangeRateCurrencyCatalogProtocol,
)
from src.modules.currency.application.port.publication_lock import (
    ExchangeRatePublicationLockProtocol,
)
from src.modules.currency.domain.aggregate import ExchangeRateBook
from src.modules.currency.domain.repository import ExchangeRateBookRepositoryProtocol
from src.modules.currency.domain.value_object.quote import ExchangeRateQuoteVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.currency import CurrencyVO


class RefreshExchangeRatesHandler:
    """Загружает NBU до первого SQL, затем проверяет и публикует всю книгу."""

    def __init__(
        self,
        source: ExchangeRateSourceProtocol,
        catalog: ExchangeRateCurrencyCatalogProtocol,
        repository: ExchangeRateBookRepositoryProtocol,
        publication_lock: ExchangeRatePublicationLockProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает порты, собранные снаружи на одной ленивой сессии UoW."""
        self._source = source
        self._catalog = catalog
        self._repository = repository
        self._publication_lock = publication_lock
        self._clock = clock

    async def execute(
        self, command: RefreshExchangeRatesCommand
    ) -> RefreshExchangeRatesResultDTO:
        """Обновляет книгу без commit и возвращает конкретный результат сценария."""
        started = self._clock.now()
        today = started.astimezone(ZoneInfo("Europe/Kyiv")).date()
        snapshot = await self._source.fetch(today)
        checked = self._clock.now()
        if (
            snapshot.effective_date != today
            or checked.astimezone(ZoneInfo("Europe/Kyiv")).date() != today
        ):
            raise ExchangeRateSourceError(
                "Source date differs from the current Kyiv date."
            )
        records = {
            item.code: item
            for item in await self._catalog.get_active(
                tuple(quote.code for quote in snapshot.quotes)
            )
        }
        quotes: list[ExchangeRateQuoteVO] = []
        unknown = metals = 0
        for quote in snapshot.quotes:
            record = records.get(quote.code)
            if record is None:
                unknown += 1
                continue
            if record.is_metal:
                metals += 1
                continue
            if record.numeric_code != quote.numeric_code:
                raise ExchangeRateCatalogMismatchError(
                    "Currency numeric code mismatch."
                )
            quotes.append(ExchangeRateQuoteVO(CurrencyVO(quote.code), quote.rate))
        # Валидируем полный набор до блокировки, но инварианты проверяет агрегат.
        candidate = ExchangeRateBook.create(
            effective_date=today,
            request_started_at=started,
            checked_at=checked,
            quotes=tuple(quotes),
        )
        await self._publication_lock.acquire()
        book = await self._repository.get()
        if book is None:
            book = candidate
        else:
            book.refresh(
                effective_date=today,
                request_started_at=started,
                checked_at=checked,
                quotes=candidate.quotes,
            )
        await self._repository.save(book)
        return RefreshExchangeRatesResultDTO(
            "nbu",
            book.snapshot_id.uuid,
            len(book.quotes),
            book.effective_date,
            book.checked_at,
            unknown,
            metals,
        )
