from __future__ import annotations

import re

from fastapi import Request

_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def normalize_host(host: str) -> str:
    """Normalize a DNS Host authority without interpreting URL userinfo or paths."""

    normalized = host.strip().lower()
    if not normalized or len(normalized) > 259:
        return ""
    hostname, separator, port = normalized.partition(":")
    if separator and (
        not port.isascii()
        or not port.isdecimal()
        or len(port) > 5
        or not 0 < int(port) <= 65535
    ):
        return ""
    if len(hostname) > 253 or any(
        not _DNS_LABEL.fullmatch(label) for label in hostname.split(".")
    ):
        return ""
    return hostname


def extract_request_host(request: Request) -> str:
    """Достает host из FastAPI request и нормализует его."""
    raw_host = request.headers.get("host", "")
    return normalize_host(raw_host)
