from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import socket
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx


@dataclass(frozen=True, slots=True)
class FetchResult:
    path: Path
    checksum: str
    content_type: str
    size: int
    etag: str | None = None
    last_modified: str | None = None


class HttpRemoteFileFetcher:
    """Bounded streaming HTTPS fetcher with redirect and DNS SSRF checks."""

    def __init__(
        self,
        *,
        max_bytes: int = 64 * 1024 * 1024,
        timeout_seconds: float = 30,
        max_redirects: int = 3,
        allow_http: bool = False,
    ) -> None:
        self.max_bytes = max_bytes
        self.timeout_seconds = timeout_seconds
        self.max_redirects = max_redirects
        self.allow_http = allow_http

    async def fetch(self, url: str) -> FetchResult:
        current = url
        tmp_path: Path | None = None
        try:
            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=httpx.Timeout(self.timeout_seconds),
            ) as client:
                for redirect_count in range(self.max_redirects + 1):
                    await self._validate_url(current)
                    async with client.stream("GET", current) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            if redirect_count >= self.max_redirects:
                                raise ValueError(
                                    "Remote source has too many redirects."
                                )
                            location = response.headers.get("location")
                            if not location:
                                raise ValueError(
                                    "Remote source redirect has no location."
                                )
                            current = urljoin(current, location)
                            continue
                        response.raise_for_status()
                        with tempfile.NamedTemporaryFile(
                            prefix="dnk-price-list-", delete=False
                        ) as target:
                            tmp_path = Path(target.name)
                            digest = hashlib.sha256()
                            size = 0
                            async for chunk in response.aiter_bytes():
                                size += len(chunk)
                                if size > self.max_bytes:
                                    raise ValueError(
                                        "Remote source exceeds the size limit."
                                    )
                                digest.update(chunk)
                                target.write(chunk)
                        return FetchResult(
                            path=tmp_path,
                            checksum=digest.hexdigest(),
                            content_type=response.headers.get("content-type", ""),
                            size=size,
                            etag=response.headers.get("etag"),
                            last_modified=response.headers.get("last-modified"),
                        )
            raise ValueError("Remote source could not be downloaded.")
        except Exception:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)
            raise

    async def _validate_url(self, url: str) -> None:
        parsed = urlsplit(url)
        schemes = {"https", "http"} if self.allow_http else {"https"}
        if parsed.scheme not in schemes or not parsed.hostname:
            raise ValueError("Price list source must use an HTTPS URL.")
        if parsed.username or parsed.password:
            raise ValueError("Credentials in source URLs are not allowed.")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port not in ({443, 80} if self.allow_http else {443}):
            raise ValueError("Source URL port is not allowed.")
        addresses = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM),
        )
        if not addresses:
            raise ValueError("Source hostname does not resolve.")
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise ValueError("Source URL resolves to a non-public address.")
