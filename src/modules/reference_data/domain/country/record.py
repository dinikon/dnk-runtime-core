from dataclasses import dataclass
from src.modules.reference_data.domain.codes import CountryCode


@dataclass(frozen=True, slots=True)
class Country:
    code: CountryCode
    alpha3: str
    numeric_code: str
    name: str
