from __future__ import annotations

from fastapi import Request


def normalize_host(host: str) -> str:
    normalized = host.strip().lower()
    if not normalized:
        return ""
    return normalized.split(":", 1)[0]


def extract_request_host(request: Request) -> str:
    raw_host = request.url.hostname or request.headers.get("host", "")
    return normalize_host(raw_host)
