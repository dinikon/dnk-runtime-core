from __future__ import annotations

from typing import Any

import httpx

from src.modules.communication.application.ports import (
    ProviderHttpResponse,
)


class HttpxProviderHttpClient:
    """httpx-backed provider HTTP client."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self._timeout_seconds = timeout_seconds

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        json_body: Any,
        basic_auth: tuple[str, str] | None = None,
    ) -> ProviderHttpResponse:
        """Execute an HTTP request and normalize JSON/text response payload."""
        auth = basic_auth if basic_auth is not None else None
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_body,
                auth=auth,
            )

        try:
            payload: Any = response.json()
        except ValueError:
            payload = {"text": response.text}

        return ProviderHttpResponse(
            status_code=response.status_code,
            payload=payload,
        )


__all__ = ["HttpxProviderHttpClient"]
