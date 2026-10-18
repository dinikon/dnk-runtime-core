import json
import re
from datetime import date, datetime, UTC
from decimal import Context, Decimal, ROUND_HALF_UP, localcontext
from email.utils import parsedate_to_datetime
import httpx
from src.modules.currency.domain.value_object.quote import ExchangeRateQuoteVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.currency.domain.error import InvalidExchangeRateError
from src.modules.currency.application.port.source import (
    SourceExchangeRateDTO,
    SourceExchangeRateSnapshotDTO,
)
from src.modules.currency.infrastructure.nbu.error import (
    NbuHttpError,
    NbuRateLimitError,
    NbuResponseError,
    NbuTransportError,
)
from src.modules.shared.domain.time.clock_port import ClockPort

NBU_URL = "https://bank.gov.ua/NBU_Exchange/exchange"


class NbuExchangeRateSource:
    """Получает основной JSON NBU и переводит Amount/Units в UAH за единицу."""

    def __init__(self, client: httpx.AsyncClient, clock: ClockPort) -> None:
        """Принимает внешний HTTP-клиент и часы без SQL-зависимостей."""
        self._client = client
        self._clock = clock

    async def fetch(self, effective_date: date) -> SourceExchangeRateSnapshotDTO:
        """Запрашивает явную дату, проверяет весь ответ и не делает SQL или повторов."""
        try:
            response = await self._client.get(
                NBU_URL,
                params={"date": effective_date.strftime("%d.%m.%Y"), "json": ""},
                timeout=10,
            )
        except httpx.RequestError as exc:
            raise NbuTransportError("NBU request unavailable.") from exc
        if response.status_code == 429:
            raise NbuRateLimitError(
                self._retry_after(
                    response.headers.get("Retry-After"), self._clock.now()
                )
            )
        if not response.is_success:
            raise NbuHttpError(response.status_code)
        try:
            raw = json.loads(
                response.content,
                parse_float=Decimal,
                parse_constant=self._reject_constant,
            )
            if not isinstance(raw, list) or not raw:
                raise NbuResponseError("NBU returned no quotes.")
            quotes: list[SourceExchangeRateDTO] = []
            seen: set[str] = set()
            for item in raw:
                if not isinstance(item, dict):
                    raise NbuResponseError("NBU quote must be an object.")
                code = item["CurrencyCodeL"]
                numeric_code = item["CurrencyCode"]
                amount = item["Amount"]
                units = item["Units"]
                if not isinstance(code, str) or not re.fullmatch(
                    r"[A-Z]{3}", code.strip()
                ):
                    raise NbuResponseError("Invalid NBU currency code.")
                code = code.strip()
                if code in seen:
                    raise NbuResponseError("Duplicate NBU currency.")
                seen.add(code)
                if not isinstance(numeric_code, str) or not re.fullmatch(
                    r"[0-9]{3}", numeric_code
                ):
                    raise NbuResponseError("Invalid NBU numeric code.")
                if (
                    datetime.strptime(item["StartDate"], "%d.%m.%Y").date()
                    != effective_date
                ):
                    raise NbuResponseError(
                        "NBU effective date differs from requested date."
                    )
                if (
                    type(units) is not int
                    or units <= 0
                    or isinstance(amount, bool)
                    or not isinstance(amount, (int, Decimal))
                ):
                    raise NbuResponseError("Invalid NBU amount or units.")
                amount = Decimal(amount)
                if not amount.is_finite() or amount <= 0:
                    raise NbuResponseError("NBU amount must be positive and finite.")
                with localcontext(Context(prec=60, rounding=ROUND_HALF_UP)):
                    rate = amount / Decimal(units)
                quotes.append(
                    SourceExchangeRateDTO(
                        code,
                        numeric_code,
                        ExchangeRateQuoteVO(CurrencyVO(code), rate).rate,
                    )
                )
            return SourceExchangeRateSnapshotDTO(effective_date, tuple(quotes))
        except (
            ValueError,
            TypeError,
            KeyError,
            ArithmeticError,
            UnicodeError,
            InvalidExchangeRateError,
        ) as exc:
            raise NbuResponseError("Malformed NBU response.") from exc

    @staticmethod
    def _reject_constant(value: str) -> None:
        """Отклоняет JSON NaN/Infinity вместо неявного float."""
        raise NbuResponseError("Nonfinite JSON number.")

    @staticmethod
    def _retry_after(value: str | None, now: datetime) -> float | None:
        """Разбирает Retry-After как секунды либо HTTP date."""
        if value is None:
            return None
        try:
            if value.strip().isdigit():
                return float(int(value.strip()))
            deadline = parsedate_to_datetime(value)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=UTC)
            return max(0.0, (deadline - now).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return None
