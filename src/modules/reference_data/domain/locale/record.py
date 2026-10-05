from dataclasses import dataclass
from src.modules.reference_data.domain.codes import (
    CountryCode,
    LocaleCode,
    LocaleRegionCode,
)


@dataclass(frozen=True, slots=True)
class Locale:
    code: LocaleCode
    language_code: str
    script_code: str | None
    region_code: LocaleRegionCode | None
    country_code: CountryCode | None
    name: str
