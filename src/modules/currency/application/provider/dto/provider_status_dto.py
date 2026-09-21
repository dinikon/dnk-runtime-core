from dataclasses import dataclass
from datetime import date
from src.modules.currency.application.rate_import.dto.rate_import_dto import (
    RateImportDTO,
)


@dataclass(frozen=True, slots=True)
class ProviderStatusDTO:
    """Latest global import outcome and available effective rate date."""

    last_import: RateImportDTO | None
    last_available_rate_date: date | None


__all__ = ["ProviderStatusDTO"]
