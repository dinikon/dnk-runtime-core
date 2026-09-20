from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import socket
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import httpx
from src.modules.price_lists.application.sync_run.options import ImportOptions
from src.modules.price_lists.application.sync_run.dto.source_dto import FetchResult
from src.modules.price_lists.domain.price_list.error import PriceListValidationError


class SourceDownloadError(RuntimeError):
    """Безопасная ошибка внешнего источника без URL или токенов."""


class HttpRemoteFileFetcher:
    """Потоковый fetcher с закреплённым проверенным IP и cleanup."""

    def __init__(
        self,
        *,
        options: ImportOptions | None = None,
        max_bytes: int | None = None,
        timeout_seconds: float = 30,
        max_redirects: int = 3,
        allow_http: bool = False,
    ):
        self.options = options or ImportOptions()
        self.max_bytes = max_bytes or self.options.max_download_bytes
        self.timeout_seconds = timeout_seconds
        self.max_redirects = max_redirects
        self.allow_http = allow_http

    @asynccontextmanager
    async def open(self, url: str):
        """Владеет временным файлом до завершения обработки."""
        fetched = await self.fetch(url)
        try:
            yield fetched
        finally:
            await asyncio.to_thread(fetched.path.unlink, missing_ok=True)

    async def fetch(self, url: str) -> FetchResult:
        """Возвращает локальный источник; при ошибке удаляет незавершённый файл."""
        current = url
        tmp_path = None
        try:
            # A new transport per redirect prevents pooling different SNI hosts
            # under the same validated IP, and trust_env avoids proxy bypass.
            for redirect_count in range(self.max_redirects + 1):
                address = await self._validate_url(current)
                original = httpx.URL(current)
                pinned = original.copy_with(host=address)
                host = original.netloc.decode("ascii")
                async with httpx.AsyncClient(
                    follow_redirects=False,
                    trust_env=False,
                    timeout=httpx.Timeout(self.timeout_seconds),
                ) as client:
                    async with client.stream(
                        "GET",
                        pinned,
                        headers={"Host": host},
                        extensions={"sni_hostname": original.host},
                    ) as response:
                        if response.status_code in (301, 302, 303, 307, 308):
                            location = response.headers.get("location")
                            if not location or redirect_count >= self.max_redirects:
                                raise SourceDownloadError("Invalid redirect chain.")
                            current = urljoin(current, location)
                            continue
                        if not 200 <= response.status_code < 300:
                            raise SourceDownloadError(
                                "Remote source returned an unsuccessful response."
                            )
                        declared = response.headers.get("content-length")
                        if declared and int(declared) > self.max_bytes:
                            raise SourceDownloadError(
                                "Remote source exceeds the size limit."
                            )
                        creation = asyncio.create_task(
                            asyncio.to_thread(
                                tempfile.NamedTemporaryFile,
                                prefix="dnk-price-list-",
                                delete=False,
                            )
                        )
                        try:
                            target = await asyncio.shield(creation)
                        except asyncio.CancelledError:
                            target = await creation
                            await asyncio.to_thread(target.close)
                            await asyncio.to_thread(
                                Path(target.name).unlink, missing_ok=True
                            )
                            raise
                        tmp_path = Path(target.name)
                        digest = hashlib.sha256()
                        size = 0
                        try:
                            async for chunk in response.aiter_bytes(
                                chunk_size=64 * 1024
                            ):
                                size += len(chunk)
                                if size > min(
                                    self.max_bytes, self.options.max_temp_bytes
                                ):
                                    raise SourceDownloadError(
                                        "Remote source exceeds the size limit."
                                    )
                                digest.update(chunk)
                                write = asyncio.create_task(
                                    asyncio.to_thread(target.write, chunk)
                                )
                                try:
                                    await asyncio.shield(write)
                                except asyncio.CancelledError:
                                    await write
                                    raise
                        finally:
                            await asyncio.to_thread(target.close)
                        return FetchResult(
                            tmp_path,
                            digest.hexdigest(),
                            response.headers.get("content-type", ""),
                            size,
                            response.headers.get("etag"),
                            response.headers.get("last-modified"),
                        )
            raise SourceDownloadError("Remote source could not be downloaded.")
        except BaseException as exc:
            if tmp_path is not None:
                await asyncio.to_thread(tmp_path.unlink, missing_ok=True)
            if isinstance(exc, (httpx.HTTPError, OSError, ValueError)):
                raise SourceDownloadError(
                    "Remote source could not be downloaded."
                ) from None
            raise

    async def _validate_url(self, url: str) -> str:
        parsed = urlsplit(url)
        schemes = {"https", "http"} if self.allow_http else {"https"}
        try:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except ValueError:
            raise PriceListValidationError("Invalid source URL port.") from None
        if (
            parsed.scheme not in schemes
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or port not in ({443, 80} if self.allow_http else {443})
        ):
            raise PriceListValidationError(
                "Source must use HTTPS without credentials or a custom port."
            )
        addresses = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname, port, type=socket.SOCK_STREAM
        )
        if not addresses:
            raise PriceListValidationError("Source hostname does not resolve.")
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise PriceListValidationError(
                    "Source resolves to a non-public address."
                )
        return addresses[0][4][0]


__all__ = ["FetchResult", "HttpRemoteFileFetcher", "SourceDownloadError"]
