from __future__ import annotations

from fastapi import Request


def normalize_host(host: str) -> str:
    """Нормализует host: trim, lowercase и удаление port."""

    normalized = host.strip().lower()
    if not normalized:
        return ""
    return normalized.split(":", 1)[0]


def extract_request_host(request: Request) -> str:
    """Достает host из FastAPI request и нормализует его."""
    raw_host = request.url.hostname or request.headers.get("host", "")
    return normalize_host(raw_host)
