from dataclasses import dataclass
from src.modules.reference_data.domain.codes import CurrencyCode


@dataclass(frozen=True, slots=True)
class Currency:
    code: CurrencyCode
    numeric_code: str | None
    name: str
    minor_units: int | None
