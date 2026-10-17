import asyncio
import ipaddress
import json
import socket
from typing import Any
from urllib.parse import urlsplit
import httpx
from src.modules.channels.application.publication_import_run.error import (
    PublicationSourceError,
)


class PublicationJsonClient:
    """Читает ограниченный JSON по HTTPS с закреплённым публичным IP."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        max_bytes: int = 16 * 1024 * 1024,
        timeout: float = 30,
    ) -> None:
        """Принимает необязательный HTTP клиент для контрактных тестов адаптера."""
        self._client, self._max_bytes = client, max_bytes
        self._timeout = timeout

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, str | int],
        unauthorized_code: str = "access_denied",
    ) -> tuple[Any, dict[str, str]]:
        """Читает GET без редиректов, прокси, логирования URL и ответа."""
        return await self._request(
            "GET",
            url,
            headers=headers,
            params=params,
            unauthorized_code=unauthorized_code,
        )

    async def post(
        self, url: str, *, headers: dict[str, str], payload: dict[str, str]
    ) -> tuple[Any, dict[str, str]]:
        """Отправляет JSON только на фиксированный endpoint авторизации Rozetka."""
        if url != "https://api-seller.rozetka.com.ua/sites":
            raise PublicationSourceError("invalid_source_url")
        return await self._request(
            "POST", url, headers=headers, params={}, payload=payload
        )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, str | int],
        payload: dict[str, str] | None = None,
        unauthorized_code: str = "access_denied",
    ) -> tuple[Any, dict[str, str]]:
        """Закрепляет публичный адрес и переводит ошибки в безопасные коды."""
        try:
            parsed = urlsplit(url)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.port not in (None, 443)
            ):
                raise PublicationSourceError("invalid_source_url")
            if self._client is not None:
                return await self._read(
                    self._client,
                    url,
                    method=method,
                    headers=headers,
                    params=params,
                    payload=payload,
                    unauthorized_code=unauthorized_code,
                )
            addresses = await asyncio.get_running_loop().getaddrinfo(
                parsed.hostname, 443, type=socket.SOCK_STREAM
            )
            if not addresses or any(
                not ipaddress.ip_address(row[4][0]).is_global for row in addresses
            ):
                raise PublicationSourceError("invalid_source_url")
            original = httpx.URL(url)
            pinned = original.copy_with(host=addresses[0][4][0])
            async with httpx.AsyncClient(
                timeout=self._timeout, follow_redirects=False, trust_env=False
            ) as client:
                return await self._read(
                    client,
                    str(pinned),
                    method=method,
                    headers={**headers, "Host": original.netloc.decode("ascii")},
                    params=params,
                    extensions={"sni_hostname": original.host},
                    payload=payload,
                    unauthorized_code=unauthorized_code,
                )
        except (httpx.HTTPError, OSError, TimeoutError):
            raise PublicationSourceError("source_unavailable", retryable=True) from None
        except (ValueError, json.JSONDecodeError):
            raise PublicationSourceError("invalid_source_data") from None

    async def _read(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        method: str,
        headers: dict[str, str],
        params: dict[str, str | int],
        extensions: dict[str, Any] | None = None,
        payload: dict[str, str] | None = None,
        unauthorized_code: str = "access_denied",
    ) -> tuple[Any, dict[str, str]]:
        """Ограничивает размер уже распакованного ответа и переводит HTTP отказы в коды."""
        async with client.stream(
            method,
            url,
            headers=headers,
            params=params,
            extensions=extensions,
            json=payload,
            follow_redirects=False,
        ) as response:
            if response.status_code == 401:
                raise PublicationSourceError(unauthorized_code)
            if response.status_code == 403:
                raise PublicationSourceError("access_denied")
            if response.status_code == 429 or response.status_code >= 500:
                raise PublicationSourceError("source_unavailable", retryable=True)
            if not 200 <= response.status_code < 300:
                raise PublicationSourceError("source_request_rejected")
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > self._max_bytes:
                    raise PublicationSourceError("source_response_too_large")
            return json.loads(data), dict(response.headers)
