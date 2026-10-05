from dataclasses import dataclass
from src.modules.reference_data.domain.codes import CountryCode, TimeZoneCode


@dataclass(frozen=True, slots=True)
class TimeZone:
    code: TimeZoneCode
    country_codes: tuple[CountryCode, ...]
