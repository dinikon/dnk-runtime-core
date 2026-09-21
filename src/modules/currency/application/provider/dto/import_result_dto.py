from dataclasses import dataclass
from src.modules.currency.domain.rate_import.value_object.id import RateImportIdVO


@dataclass(frozen=True, slots=True)
class ImportResultDTO:
    """Committed counts and status of a global synchronization attempt."""

    id: RateImportIdVO
    status: str
    received_count: int
    created_count: int
    updated_count: int


__all__ = ["ImportResultDTO"]
