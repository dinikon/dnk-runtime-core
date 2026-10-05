from __future__ import annotations

import re
from datetime import datetime

from src.modules.reference_data.application.port.catalog import (
    CatalogRepositoryPort,
    SourcePort,
    SourceSnapshot,
)
from src.modules.reference_data.domain.country.record import Country
from src.modules.reference_data.domain.currency.record import Currency
from src.modules.reference_data.domain.locale.record import Locale
from src.modules.reference_data.domain.locale.subtags import parse_locale_subtags
from src.modules.reference_data.domain.time_zone.record import TimeZone
from src.modules.shared.domain.time.clock_port import ClockPort

MINIMUM_COUNTS = {
    "countries": 200,
    "currencies": 150,
    "locales": 100,
    "time-zones": 250,
}
REQUIRED_CODES = {
    "countries": {"UA"},
    "currencies": {"UAH", "USD", "EUR"},
    "locales": {"uk", "uk-UA", "ru-UA"},
    "time-zones": {"Europe/Kyiv"},
}


class InvalidSourceSnapshotError(ValueError):
    """External data is malformed or suspiciously incomplete."""


def validate_snapshot(dataset: str, snapshot: SourceSnapshot) -> None:
    records = snapshot.records
    if len(records) < MINIMUM_COUNTS[dataset]:
        raise InvalidSourceSnapshotError(f"{dataset}: incomplete source snapshot")
    codes = [record.code for record in records]
    if len(set(codes)) != len(codes) or not REQUIRED_CODES[dataset] <= set(codes):
        raise InvalidSourceSnapshotError(f"{dataset}: duplicate or missing codes")
    for record in records:
        code = record.code
        if dataset == "countries":
            if (
                not isinstance(record, Country)
                or not re.fullmatch(r"[A-Z]{2}", code)
                or not re.fullmatch(r"[A-Z]{3}", record.alpha3)
                or not re.fullmatch(r"[0-9]{3}", record.numeric_code)
            ):
                raise InvalidSourceSnapshotError(f"Invalid country {code}")
        elif dataset == "currencies":
            if (
                not isinstance(record, Currency)
                or not re.fullmatch(r"[A-Z]{3}", code)
                or (
                    record.numeric_code is not None
                    and not re.fullmatch(r"[0-9]{3}", record.numeric_code)
                )
                or (record.minor_units is not None and not 0 <= record.minor_units <= 9)
            ):
                raise InvalidSourceSnapshotError(f"Invalid currency {code}")
        elif dataset == "locales":
            if not isinstance(record, Locale):
                raise InvalidSourceSnapshotError(f"Invalid locale {code}")
            try:
                language, script, region = parse_locale_subtags(code)
            except ValueError as exc:
                raise InvalidSourceSnapshotError(f"Invalid locale {code}") from exc
            if (record.language_code, record.script_code, record.region_code) != (
                language,
                script,
                region,
            ):
                raise InvalidSourceSnapshotError(f"Inconsistent locale subtags {code}")
            if record.country_code is not None and (
                record.country_code != record.region_code
                or not re.fullmatch(r"[A-Z]{2}", record.country_code)
            ):
                raise InvalidSourceSnapshotError(f"Invalid locale country {code}")
        elif dataset == "time-zones":
            if not isinstance(record, TimeZone) or not re.fullmatch(
                r"[A-Za-z0-9_+\-/]+", code
            ):
                raise InvalidSourceSnapshotError(f"Invalid time zone {code}")
        if dataset != "time-zones" and not record.name.strip():
            raise InvalidSourceSnapshotError(f"Missing name for {code}")


class SyncReferenceDataHandler:
    """Loads one dataset through a source port and persists a validated snapshot."""

    def __init__(
        self,
        dataset: str,
        source: SourcePort,
        repository: CatalogRepositoryPort,
        clock: ClockPort,
    ) -> None:
        if dataset not in MINIMUM_COUNTS:
            raise ValueError(f"Unknown reference dataset: {dataset}")
        self._dataset = dataset
        self._source = source
        self._repository = repository
        self._clock = clock

    async def execute(self) -> tuple[str, int, datetime]:
        snapshot = await self._source.fetch()
        validate_snapshot(self._dataset, snapshot)
        previous_count = await self._repository.last_count(self._dataset)
        if previous_count and len(snapshot.records) < previous_count * 0.9:
            raise InvalidSourceSnapshotError(
                f"{self._dataset}: source shrank by more than ten percent"
            )
        now = self._clock.now()
        await self._repository.replace_snapshot(self._dataset, snapshot, now)
        return snapshot.version, len(snapshot.records), now
