import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from typing import Protocol

import httpx
from pydantic import TypeAdapter

from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.domain.types import JsonValue


@dataclass(frozen=True, slots=True)
class JsonHttpResponse:
    """Данные ответа и заголовки пагинации без транспортного клиента."""

    data: JsonValue
    headers: dict[str, str]


class JsonHttp(Protocol):
    """Минимальный HTTP-порт пакетов для детерминированных contract-тестов."""

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: JsonValue = None,
    ) -> JsonValue:
        """Возвращает ограниченный JSON либо безопасную ошибку."""
        ...

    async def request_response(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: JsonValue = None,
    ) -> JsonHttpResponse:
        """Возвращает JSON вместе с заголовками для страничных API."""
        ...

    async def request_bytes(self, url: str) -> bytes:
        """Читает публичный файл без credentials, redirect и неограниченного тела."""
        ...


class PublicHttpsTransport(httpx.AsyncBaseTransport):
    """Закрепляет проверенный публичный IP и сохраняет исходные Host и TLS SNI."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Проверяет все DNS-ответы перед соединением с числовым адресом."""
        if request.url.scheme != "https":
            raise VerificationFailure("endpoint_invalid")
        host, port = request.url.host, request.url.port or 443
        answers = await asyncio.get_running_loop().getaddrinfo(
            host, port, type=socket.SOCK_STREAM
        )
        addresses = [answer[4][0] for answer in answers]
        if not addresses or any(
            not ipaddress.ip_address(address).is_global for address in addresses
        ):
            raise VerificationFailure("endpoint_invalid")
        extensions = {**request.extensions, "sni_hostname": host}
        pinned = httpx.Request(
            request.method,
            request.url.copy_with(host=addresses[0]),
            headers=request.headers,
            stream=request.stream,
            extensions=extensions,
        )
        # Отдельное соединение исключает reuse IP с TLS-контекстом другого host.
        transport = httpx.AsyncHTTPTransport(retries=0)
        try:
            response = await transport.handle_async_request(pinned)
            chunks, size = [], 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > 10 * 1024 * 1024:
                    raise VerificationFailure("provider_response_invalid")
                chunks.append(chunk)
            return httpx.Response(
                response.status_code,
                headers={
                    key: value
                    for key, value in response.headers.items()
                    if key not in ("content-encoding", "content-length")
                },
                content=b"".join(chunks),
                request=request,
            )
        finally:
            await transport.aclose()


class SafeJsonHttp:
    """HTTP-клиент с ограничениями времени, тела и безопасным отображением ошибок."""

    async def request_bytes(self, url: str) -> bytes:
        """Использует тот же HTTPS/DNS guard; секреты API не передаются на media host."""
        try:
            async with httpx.AsyncClient(
                transport=PublicHttpsTransport(),
                trust_env=False,
                follow_redirects=False,
                timeout=10,
            ) as client:
                response = await client.get(url)
            if response.status_code != 200:
                raise VerificationFailure("content_media_unconfirmed")
            return response.content
        except (httpx.TimeoutException, TimeoutError):
            raise VerificationFailure("network_timeout", retryable=True) from None
        except (httpx.RequestError, OSError, ValueError):
            raise VerificationFailure("content_media_unconfirmed") from None

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: JsonValue = None,
    ) -> JsonValue:
        """Сохраняет существующий контракт verifier без HTTP-метаданных."""
        return (
            await self.request_response(method, url, headers=headers, body=body)
        ).data

    async def request_response(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: JsonValue = None,
    ) -> JsonHttpResponse:
        """Выполняет запрос без redirect, proxy из окружения и логирования payload."""
        try:
            async with httpx.AsyncClient(
                transport=PublicHttpsTransport(),
                trust_env=False,
                follow_redirects=False,
                timeout=10,
            ) as client:
                response = await client.request(method, url, headers=headers, json=body)
            if response.status_code == 401:
                raise VerificationFailure("invalid_credentials")
            if response.status_code == 403:
                raise VerificationFailure("permission_missing")
            if response.status_code == 429:
                raise VerificationFailure("rate_limited", retryable=True)
            if response.status_code >= 500:
                raise VerificationFailure("provider_unavailable", retryable=True)
            if 300 <= response.status_code < 400:
                raise VerificationFailure("endpoint_redirected")
            if response.status_code != 200:
                raise VerificationFailure("provider_response_invalid")
            return JsonHttpResponse(
                TypeAdapter(JsonValue).validate_json(response.content),
                {key.lower(): value for key, value in response.headers.items()},
            )
        except (httpx.TimeoutException, TimeoutError):
            raise VerificationFailure("network_timeout", retryable=True) from None
        except (httpx.RequestError, OSError):
            raise VerificationFailure("endpoint_unreachable", retryable=True) from None
        except (ValueError,):
            raise VerificationFailure("provider_response_invalid") from None
