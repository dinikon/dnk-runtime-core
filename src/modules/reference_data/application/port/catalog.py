from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Protocol, TypeVar

from src.modules.reference_data.domain.country.record import Country
from src.modules.reference_data.domain.currency.record import Currency
from src.modules.reference_data.domain.locale.record import Locale
from src.modules.reference_data.domain.time_zone.record import TimeZone

RecordT = TypeVar("RecordT", Country, Currency, Locale, TimeZone)


@dataclass(frozen=True, slots=True)
class SourceSnapshot(Generic[RecordT]):
    source: str
    version: str
    records: tuple[RecordT, ...]


class SourcePort(Protocol[RecordT]):
    async def fetch(self) -> SourceSnapshot[RecordT]: ...


class CatalogRepositoryPort(Protocol):
    async def last_count(self, dataset: str) -> int | None: ...

    async def list_countries(self) -> list[Country]: ...
    async def list_currencies(self) -> list[Currency]: ...
    async def list_locales(self) -> list[Locale]: ...
    async def has_active_locale(self, code: str) -> bool: ...
    async def list_time_zones(self) -> list[TimeZone]: ...
    async def replace_snapshot(
        self, dataset: str, snapshot: SourceSnapshot, now: datetime
    ) -> None: ...
