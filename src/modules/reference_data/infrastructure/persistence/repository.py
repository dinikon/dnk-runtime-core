from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import hashlib

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.reference_data.application.port.catalog import SourceSnapshot
from src.modules.reference_data.domain.codes import (
    CountryCode,
    CurrencyCode,
    LocaleCode,
    LocaleRegionCode,
    TimeZoneCode,
)
from src.modules.reference_data.domain.country.record import Country
from src.modules.reference_data.domain.currency.record import Currency
from src.modules.reference_data.domain.locale.record import Locale
from src.modules.reference_data.domain.time_zone.record import TimeZone
from src.modules.reference_data.infrastructure.persistence.models.country import (
    CountryModel,
)
from src.modules.reference_data.infrastructure.persistence.models.currency import (
    CurrencyModel,
)
from src.modules.reference_data.infrastructure.persistence.models.locale import (
    LocaleModel,
)
from src.modules.reference_data.infrastructure.persistence.models.sync_state import (
    ReferenceSyncStateModel,
)
from src.modules.reference_data.infrastructure.persistence.models.time_zone import (
    CountryTimeZoneModel,
    TimeZoneModel,
)


class SqlAlchemyCatalogRepository:
    """Reads public catalogs and updates one dataset in the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def last_count(self, dataset: str) -> int | None:
        return await self._session.scalar(
            select(ReferenceSyncStateModel.row_count).where(
                ReferenceSyncStateModel.dataset == dataset
            )
        )

    async def list_countries(self) -> list[Country]:
        models = (
            await self._session.scalars(
                select(CountryModel)
                .where(CountryModel.active.is_(True))
                .order_by(CountryModel.code)
            )
        ).all()
        return [
            Country(CountryCode(m.code), m.alpha3, m.numeric_code, m.name)
            for m in models
        ]

    async def list_currencies(self) -> list[Currency]:
        models = (
            await self._session.scalars(
                select(CurrencyModel)
                .where(CurrencyModel.active.is_(True))
                .order_by(CurrencyModel.code)
            )
        ).all()
        return [
            Currency(CurrencyCode(m.code), m.numeric_code, m.name, m.minor_units)
            for m in models
        ]

    async def list_locales(self) -> list[Locale]:
        models = (
            await self._session.scalars(
                select(LocaleModel)
                .where(LocaleModel.active.is_(True))
                .order_by(LocaleModel.code)
            )
        ).all()
        return [
            Locale(
                LocaleCode(m.code),
                m.language_code,
                m.script_code,
                LocaleRegionCode(m.region_code) if m.region_code else None,
                CountryCode(m.country_code) if m.country_code else None,
                m.name,
            )
            for m in models
        ]

    async def has_active_locale(self, code: str) -> bool:
        """Проверяет один код без загрузки всего справочника."""
        return bool(
            await self._session.scalar(
                select(LocaleModel.code).where(
                    LocaleModel.code == code, LocaleModel.active.is_(True)
                )
            )
        )

    async def has_active_time_zone(self, code: str) -> bool:
        """Проверяет один активный timezone без загрузки всего справочника."""
        return bool(
            await self._session.scalar(
                select(TimeZoneModel.code).where(
                    TimeZoneModel.code == code, TimeZoneModel.active.is_(True)
                )
            )
        )

    async def list_time_zones(self) -> list[TimeZone]:
        zones = (
            await self._session.scalars(
                select(TimeZoneModel)
                .where(TimeZoneModel.active.is_(True))
                .order_by(TimeZoneModel.code)
            )
        ).all()
        links = (
            await self._session.execute(
                select(
                    CountryTimeZoneModel.time_zone_code,
                    CountryTimeZoneModel.country_code,
                ).order_by(CountryTimeZoneModel.country_code)
            )
        ).all()
        countries: dict[str, list[str]] = defaultdict(list)
        for zone_code, country_code in links:
            countries[zone_code].append(country_code)
        return [
            TimeZone(
                TimeZoneCode(zone.code),
                tuple(CountryCode(code) for code in countries[zone.code]),
            )
            for zone in zones
        ]

    async def replace_snapshot(
        self, dataset: str, snapshot: SourceSnapshot, now: datetime
    ) -> None:
        key = int.from_bytes(
            hashlib.sha256(f"reference-data:{dataset}".encode()).digest()[:8],
            signed=True,
        )
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": key}
        )
        model_by_dataset = {
            "countries": CountryModel,
            "currencies": CurrencyModel,
            "locales": LocaleModel,
            "time-zones": TimeZoneModel,
        }
        model = model_by_dataset[dataset]
        rows: list[dict] = []
        for record in snapshot.records:
            if isinstance(record, Country):
                rows.append(
                    dict(
                        code=record.code,
                        alpha3=record.alpha3,
                        numeric_code=record.numeric_code,
                        name=record.name,
                        active=True,
                    )
                )
            elif isinstance(record, Currency):
                rows.append(
                    dict(
                        code=record.code,
                        numeric_code=record.numeric_code,
                        name=record.name,
                        minor_units=record.minor_units,
                        active=True,
                    )
                )
            elif isinstance(record, Locale):
                rows.append(
                    dict(
                        code=record.code,
                        language_code=record.language_code,
                        script_code=record.script_code,
                        region_code=record.region_code,
                        country_code=record.country_code,
                        name=record.name,
                        active=True,
                    )
                )
            elif isinstance(record, TimeZone):
                rows.append(dict(code=record.code, active=True))
            else:
                raise TypeError(f"Unexpected reference record: {type(record)!r}")
        codes = [row["code"] for row in rows]
        await self._session.execute(
            update(model).where(model.code.not_in(codes)).values(active=False)
        )
        for row in rows:
            statement = insert(model).values(**row)
            await self._session.execute(
                statement.on_conflict_do_update(
                    index_elements=[model.code],
                    set_={key: value for key, value in row.items() if key != "code"},
                )
            )
        if dataset == "time-zones":
            await self._session.execute(delete(CountryTimeZoneModel))
            known_countries = set(
                (await self._session.scalars(select(CountryModel.code))).all()
            )
            for zone in snapshot.records:
                for country_code in zone.country_codes:
                    if country_code in known_countries:
                        await self._session.execute(
                            insert(CountryTimeZoneModel)
                            .values(country_code=country_code, time_zone_code=zone.code)
                            .on_conflict_do_nothing()
                        )
        state = dict(
            dataset=dataset,
            source=snapshot.source,
            source_version=snapshot.version,
            last_success_at=now,
            row_count=len(rows),
        )
        statement = insert(ReferenceSyncStateModel).values(**state)
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[ReferenceSyncStateModel.dataset],
                set_={key: value for key, value in state.items() if key != "dataset"},
            )
        )
        await self._session.flush()
