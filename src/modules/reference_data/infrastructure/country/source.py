from __future__ import annotations

from src.modules.reference_data.application.port.catalog import SourceSnapshot
from src.modules.reference_data.domain.codes import CountryCode
from src.modules.reference_data.domain.country.record import Country
from src.modules.reference_data.infrastructure.source.cldr import (
    CldrClient,
    _is_iso_country,
)


class CldrCountrySource:
    def __init__(self, client: CldrClient) -> None:
        self._client = client

    async def fetch(self) -> SourceSnapshot[Country]:
        version = await self._client.version()
        mappings = (
            await self._client.read(version, "cldr-core/supplemental/codeMappings.json")
        )["supplemental"]["codeMappings"]
        current = (
            await self._client.read(
                version, "cldr-core/supplemental/territoryInfo.json"
            )
        )["supplemental"]["territoryInfo"]
        names = (
            await self._client.read(
                version, "cldr-localenames-full/main/en/territories.json"
            )
        )["main"]["en"]["localeDisplayNames"]["territories"]
        countries = []
        for code in current:
            mapping = mappings.get(code, {})
            if _is_iso_country(code, mapping, names.get(code)):
                countries.append(
                    Country(
                        CountryCode(code),
                        mapping["_alpha3"],
                        mapping["_numeric"],
                        names[code],
                    )
                )
        return SourceSnapshot("unicode-cldr", version, tuple(countries))
