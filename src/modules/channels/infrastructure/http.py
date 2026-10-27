import asyncio
import ipaddress
import socket
from typing import Protocol

import httpx
from pydantic import TypeAdapter

from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.types import JsonValue


class JsonHttp(Protocol):
    """Минимальный HTTP-порт пакетов для детерминированных contract-тестов."""

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: JsonObject | None = None,
    ) -> JsonValue:
        """Возвращает ограниченный JSON либо безопасную ошибку."""
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
                if size > 2 * 1024 * 1024:
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

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: JsonObject | None = None,
    ) -> JsonValue:
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
            return TypeAdapter(JsonValue).validate_json(response.content)
        except (httpx.TimeoutException, TimeoutError):
            raise VerificationFailure("network_timeout", retryable=True) from None
        except (httpx.RequestError, OSError):
            raise VerificationFailure("endpoint_unreachable", retryable=True) from None
        except (ValueError,):
            raise VerificationFailure("provider_response_invalid") from None
