import asyncio
from decimal import Decimal
import ipaddress
import json
import socket
from urllib.parse import urlsplit
import httpx
from src.modules.channels.application.plugin_contract import HttpResultDTO
from src.modules.channels.application.port.plugin_services import PluginCallError


class ScopedHttpTransport:
    """Ограничивает GET текущим HTTPS origin, проверенным IP и размером ответа."""

    def __init__(
        self, endpoint: str, *, max_bytes: int = 4 * 1024 * 1024, timeout: float = 30
    ) -> None:
        """Принимает пределы текущего deployment без произвольных redirects."""
        self.endpoint, self.max_bytes, self.timeout = (
            endpoint.rstrip("/"),
            max_bytes,
            timeout,
        )

    async def get(
        self,
        path: str,
        *,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResultDTO:
        """Закрепляет публичный IP и TLS SNI; не возвращает тела ошибок в логи."""
        if (
            not path.startswith("/")
            or path.startswith("//")
            or any((char in path for char in ("?", "#", "\\")))
        ):
            raise PluginCallError("invalid_request_path")
        original = httpx.URL(self.endpoint + path, params=query)
        parsed = urlsplit(str(original))
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or (parsed.port not in (None, 443))
        ):
            raise PluginCallError("unsafe_endpoint")
        try:
            async with asyncio.timeout(self.timeout):
                infos = await asyncio.get_running_loop().getaddrinfo(
                    original.host, 443, type=socket.SOCK_STREAM
                )
                addresses = tuple(dict.fromkeys((info[4][0] for info in infos)))
                if not addresses or any(
                    (not ipaddress.ip_address(value).is_global for value in addresses)
                ):
                    raise PluginCallError("unsafe_endpoint")
                safe_headers = {
                    "Accept": "application/json",
                    "Host": original.netloc.decode("ascii"),
                }
                for key, value in (headers or {}).items():
                    if key.lower() not in ("authorization", "accept"):
                        raise PluginCallError("invalid_request_header")
                    safe_headers[key] = value
                async with httpx.AsyncClient(
                    timeout=self.timeout, trust_env=False, follow_redirects=False
                ) as client:
                    async with client.stream(
                        "GET",
                        original.copy_with(host=addresses[0]),
                        headers=safe_headers,
                        extensions={"sni_hostname": original.host},
                    ) as response:
                        if response.status_code in (401, 403):
                            raise PluginCallError("permission_denied")
                        if response.status_code == 429 or response.status_code >= 500:
                            raise PluginCallError(
                                "provider_temporarily_unavailable", retryable=True
                            )
                        if not 200 <= response.status_code < 300:
                            raise PluginCallError("provider_request_rejected")
                        chunks, size = ([], 0)
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > self.max_bytes:
                                raise PluginCallError("response_too_large")
                            chunks.append(chunk)
                        body = json.loads(
                            b"".join(chunks),
                            parse_float=Decimal,
                            parse_constant=self._reject_constant,
                        )
                        return HttpResultDTO(
                            body,
                            {
                                key: value
                                for key, value in response.headers.items()
                                if key.lower() in ("x-wp-total", "x-wp-totalpages")
                            },
                        )
        except PluginCallError:
            raise
        except (httpx.HTTPError, TimeoutError, OSError):
            raise PluginCallError("network_error", retryable=True) from None
        except (ValueError, UnicodeError, RecursionError):
            raise PluginCallError("invalid_provider_response") from None

    @staticmethod
    def _reject_constant(value: str) -> None:
        """Отклоняет нестандартные NaN/Infinity в JSON провайдера."""
        raise ValueError("invalid_json_number")
