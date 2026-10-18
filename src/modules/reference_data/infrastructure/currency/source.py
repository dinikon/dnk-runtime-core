from __future__ import annotations

import httpx
from defusedxml import ElementTree

from src.modules.reference_data.application.port.catalog import SourceSnapshot
from src.modules.reference_data.domain.codes import CurrencyCode
from src.modules.reference_data.domain.currency.record import Currency

_LIST_ONE_URL = "https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml"


class SixCurrencySource:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(self) -> SourceSnapshot[Currency]:
        response = await self._client.get(_LIST_ONE_URL)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        currencies: dict[str, Currency] = {}
        for entry in root.findall(".//CcyNtry"):
            code = (entry.findtext("Ccy") or "").strip()
            if not code:
                continue
            minor = (entry.findtext("CcyMnrUnts") or "").strip()
            candidate = Currency(
                code=CurrencyCode(code),
                numeric_code=(entry.findtext("CcyNbr") or "").strip() or None,
                name=(entry.findtext("CcyNm") or "").strip(),
                minor_units=int(minor) if minor.isdigit() else None,
            )
            existing = currencies.get(code)
            if existing is not None and (
                existing.numeric_code,
                existing.minor_units,
            ) != (candidate.numeric_code, candidate.minor_units):
                raise ValueError(f"Conflicting ISO 4217 data for {code}")
            currencies.setdefault(code, candidate)
        version = root.attrib.get("Pblshd", "unknown")
        return SourceSnapshot("six-iso4217", version, tuple(currencies.values()))
