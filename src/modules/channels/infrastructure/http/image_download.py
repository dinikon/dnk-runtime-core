import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit
import httpx
from src.modules.shared.infrastructure.content.images import image_content_type
from src.modules.channels.application.publication_import.port.images import (
    DownloadedPublicationImageDTO,
)
from src.modules.channels.application.port.plugin_services import PluginCallError


class HttpsPublicationImageDownloader:
    """Загружает публичные изображения с закреплением IP и без redirects или секретов."""

    def __init__(
        self, *, max_bytes: int = 10 * 1024 * 1024, timeout: float = 30
    ) -> None:
        """Устанавливает пределы памяти и времени для одного worker шага."""
        self.max_bytes, self.timeout = max_bytes, timeout

    async def download(self, url: str) -> DownloadedPublicationImageDTO:
        """Проверяет все DNS-адреса и передаёт исходное имя только в Host/TLS SNI."""
        try:
            parsed = urlsplit(url)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.port not in (None, 443)
                or parsed.fragment
                or len(url) > 4096
            ):
                raise PluginCallError("unsafe_image_url")
            original = httpx.URL(url)
            async with asyncio.timeout(self.timeout):
                infos = await asyncio.get_running_loop().getaddrinfo(
                    original.host, 443, type=socket.SOCK_STREAM
                )
                addresses = tuple(dict.fromkeys(info[4][0] for info in infos))
                if not addresses or any(
                    not ipaddress.ip_address(ip).is_global for ip in addresses
                ):
                    raise PluginCallError("unsafe_image_url")
                async with httpx.AsyncClient(
                    timeout=self.timeout, trust_env=False, follow_redirects=False
                ) as client:
                    async with client.stream(
                        "GET",
                        original.copy_with(host=addresses[0]),
                        headers={
                            "Host": original.netloc.decode("ascii"),
                            "Accept": "*/*",
                        },
                        extensions={"sni_hostname": original.host},
                    ) as response:
                        if response.status_code != 200:
                            raise PluginCallError(
                                "image_download_failed",
                                retryable=response.status_code >= 500
                                or response.status_code == 429,
                            )
                        chunks, size = [], 0
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > self.max_bytes:
                                raise PluginCallError("image_too_large")
                            chunks.append(chunk)
                        if not size:
                            raise PluginCallError("invalid_image_file")
                        data = b"".join(chunks)
                        content_type = image_content_type(data[:4096])
                        if content_type is None:
                            raise PluginCallError("invalid_image_file")
                        return DownloadedPublicationImageDTO(data, content_type)
        except PluginCallError:
            raise
        except (httpx.HTTPError, OSError, TimeoutError):
            raise PluginCallError("image_network_error", retryable=True) from None
        except (ValueError, UnicodeError):
            raise PluginCallError("unsafe_image_url") from None
