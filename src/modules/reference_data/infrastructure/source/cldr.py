from __future__ import annotations

import re

import httpx

_RELEASE_URL = "https://api.github.com/repos/unicode-org/cldr-json/releases/latest"
_RAW_ROOT = "https://raw.githubusercontent.com/unicode-org/cldr-json"


def _is_iso_country(code: str, mapping: dict, name: str | None) -> bool:
    """Exclude CLDR's private and macro-region codes from ISO 3166-1."""
    numeric = mapping.get("_numeric", "")
    return bool(
        re.fullmatch(r"[A-Z]{2}", code)
        and re.fullmatch(r"[A-Z]{3}", mapping.get("_alpha3", ""))
        and re.fullmatch(r"[0-9]{3}", numeric)
        and int(numeric) < 900
        and name
    )


class CldrClient:
    """Fetches all files of one published CLDR JSON release."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def version(self) -> str:
        response = await self._client.get(_RELEASE_URL)
        response.raise_for_status()
        tag = response.json()["tag_name"]
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", tag):
            raise ValueError("Unexpected CLDR release tag")
        return tag

    async def read(self, version: str, path: str) -> dict:
        response = await self._client.get(f"{_RAW_ROOT}/{version}/cldr-json/{path}")
        response.raise_for_status()
        return response.json()
