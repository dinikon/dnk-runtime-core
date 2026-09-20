from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext

from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.domain_error import DomainError
from src.modules.currency.domain.models import CurrencyPair
from src.modules.currency.application.provider import ProviderRateDTO
from src.modules.currency.domain.errors import ProviderRateInvalid


def map_rates(payload, *, start_date, end_date):
    rates = {}
    try:
        for row in payload:
            code = CurrencyCodeVO(row["cc"])
            effective = datetime.strptime(row["exchangedate"], "%d.%m.%Y").date()
            calculated = (
                datetime.strptime(row["calcdate"], "%d.%m.%Y").date()
                if row.get("calcdate")
                else None
            )
            if not start_date <= effective <= end_date:
                raise ValueError("Date outside requested interval")
            units = Decimal(str(row.get("units", 1)))
            if not units.is_finite() or units <= 0:
                raise ValueError("Invalid number of currency units")
            with localcontext() as context:
                context.prec = 38
                rate = (
                    Decimal(str(row["rate_per_unit"]))
                    if "rate_per_unit" in row
                    else Decimal(str(row["rate"])) / units
                )
            item = ProviderRateDTO(
                CurrencyPair(code, CurrencyCodeVO("UAH")), rate, effective, calculated
            )
            if code.value == "UAH":
                if rate != 1:
                    raise ValueError("Invalid identity rate")
                continue
            key = (code.value, effective)
            old = rates.get(key)
            if old and old.calculated_date == calculated and old.rate != item.rate:
                raise ValueError("Conflicting provider rows")
            if old is None or (calculated or effective) >= (
                old.calculated_date or old.effective_date
            ):
                rates[key] = item
    except (KeyError, TypeError, ValueError, InvalidOperation, DomainError) as exc:
        raise ProviderRateInvalid(
            "NBU returned an invalid or conflicting rate."
        ) from exc
    return list(rates.values())
