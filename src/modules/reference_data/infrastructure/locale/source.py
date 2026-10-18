from __future__ import annotations

from src.modules.reference_data.application.port.catalog import SourceSnapshot
from src.modules.reference_data.domain.codes import (
    CountryCode,
    LocaleCode,
    LocaleRegionCode,
)
from src.modules.reference_data.domain.locale.record import Locale
from src.modules.reference_data.domain.locale.subtags import parse_locale_subtags
from src.modules.reference_data.infrastructure.source.cldr import (
    CldrClient,
    _is_iso_country,
)


class CldrLocaleSource:
    def __init__(self, client: CldrClient) -> None:
        self._client = client

    async def fetch(self) -> SourceSnapshot[Locale]:
        version = await self._client.version()
        available = (
            await self._client.read(version, "cldr-core/availableLocales.json")
        )["availableLocales"]["full"]
        names = (
            await self._client.read(
                version, "cldr-localenames-full/main/en/languages.json"
            )
        )["main"]["en"]["localeDisplayNames"]["languages"]
        countries = (
            await self._client.read(
                version, "cldr-localenames-full/main/en/territories.json"
            )
        )["main"]["en"]["localeDisplayNames"]["territories"]
        mappings = (
            await self._client.read(version, "cldr-core/supplemental/codeMappings.json")
        )["supplemental"]["codeMappings"]
        current = (
            await self._client.read(
                version, "cldr-core/supplemental/territoryInfo.json"
            )
        )["supplemental"]["territoryInfo"]
        valid_countries = {
            code
            for code in current
            if _is_iso_country(code, mappings.get(code, {}), countries.get(code))
        }
        codes = set(available) | {"uk", "ru", "uk-UA", "ru-UA"}
        locales: list[Locale] = []
        for code in sorted(codes):
            language, script, region = parse_locale_subtags(code)
            country = region if region in valid_countries else None
            name = names.get(language, language)
            if region:
                name = f"{name} ({countries.get(region, region)})"
            locales.append(
                Locale(
                    LocaleCode(code),
                    language,
                    script,
                    LocaleRegionCode(region) if region else None,
                    CountryCode(country) if country else None,
                    name,
                )
            )
        return SourceSnapshot("unicode-cldr", version, tuple(locales))
