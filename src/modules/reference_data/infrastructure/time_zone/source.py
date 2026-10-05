from __future__ import annotations

from io import BytesIO
import tarfile

import httpx

from src.modules.reference_data.application.port.catalog import SourceSnapshot
from src.modules.reference_data.domain.codes import CountryCode, TimeZoneCode
from src.modules.reference_data.domain.time_zone.record import TimeZone

_TZDATA_URL = "https://data.iana.org/time-zones/tzdata-latest.tar.gz"


class IanaTimeZoneSource:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(self) -> SourceSnapshot[TimeZone]:
        response = await self._client.get(_TZDATA_URL)
        response.raise_for_status()
        if len(response.content) > 10_000_000:
            raise ValueError("IANA archive exceeds size limit")
        with tarfile.open(fileobj=BytesIO(response.content), mode="r:gz") as archive:
            zone_file = archive.extractfile("zone1970.tab")
            country_zone_file = archive.extractfile("zone.tab")
            version_file = archive.extractfile("version")
            if zone_file is None or country_zone_file is None or version_file is None:
                raise ValueError("IANA archive lacks required files")
            lines = (
                zone_file.read().decode("utf-8").splitlines()
                + country_zone_file.read().decode("utf-8").splitlines()
            )
            version = version_file.read().decode("ascii").strip()
        zones: dict[str, TimeZone] = {}
        for line in lines:
            if not line or line.startswith("#"):
                continue
            country_list, _, code, *_ = line.split("\t")
            previous = zones.get(code)
            countries = set(previous.country_codes) if previous else set()
            countries.update(CountryCode(value) for value in country_list.split(","))
            zones[code] = TimeZone(TimeZoneCode(code), tuple(sorted(countries)))
        zones["Etc/UTC"] = TimeZone(TimeZoneCode("Etc/UTC"), ())
        return SourceSnapshot("iana-tzdb", version, tuple(zones.values()))
