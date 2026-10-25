from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Iterable
from dataclasses import dataclass
from tempfile import SpooledTemporaryFile
from typing import BinaryIO
from urllib.parse import urlsplit, urljoin, urlunsplit, quote
import httpcore
from src.modules.catalog.domain.error import InvalidCatalogValueError


def validate_public_url(url: str) -> str:
    """Отклоняет неподдержанные схемы, credentials и нестандартные порты."""
    try:
        parts = urlsplit(url)
        if (
            len(url) > 4096
            or parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.port not in {None, 80, 443}
        ):
            raise ValueError
        host = parts.hostname.rstrip(".").lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(
            (".localhost", ".local", ".internal")
        ):
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not public_address(address):
            raise ValueError
        if any(ord(character) < 32 for character in url):
            raise ValueError
        authority = (
            f"[{host}]"
            if isinstance(address, ipaddress.IPv6Address)
            else host.encode("idna").decode("ascii")
        )
        if parts.port is not None:
            authority += f":{parts.port}"
        return urlunsplit(
            (
                parts.scheme,
                authority,
                quote(parts.path, safe="/%:@!$&'()*+,;=-._~"),
                quote(parts.query, safe="%&=/:?@!$'()*+,;~-._"),
                "",
            )
        )
    except ValueError as error:
        raise InvalidCatalogValueError(
            "Нужна публичная HTTP/HTTPS-ссылка без авторизации и нестандартного порта."
        ) from error


def public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Запрещает private, reserved, multicast и IPv4-mapped обходы."""
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return public_address(address.ipv4_mapped)
    return address.is_global and not address.is_multicast and not address.is_reserved


class PublicNetworkBackend(httpcore.AnyIOBackend):
    """Проверяет DNS и соединяется с проверенным IP, сохраняя исходный TLS SNI."""

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[tuple[int, int, int | bytes]] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        """Не допускает повторного разрешения имени между проверкой и connect."""
        results = await asyncio.get_running_loop().getaddrinfo(
            host, port, type=socket.SOCK_STREAM
        )
        addresses = list(dict.fromkeys(result[4][0] for result in results))
        if not addresses or any(
            not public_address(ipaddress.ip_address(a)) for a in addresses
        ):
            raise InvalidCatalogValueError("Адрес ссылки указывает на закрытую сеть.")
        return await super().connect_tcp(
            addresses[0], port, timeout, local_address, socket_options
        )


@dataclass(frozen=True, slots=True)
class DownloadedImportFile:
    """Ограниченный spool, который вызывающий код обязан закрыть."""

    source: BinaryIO
    size: int
    content_type: str


async def download_public_file(
    url: str, limit: int, timeout_seconds: int
) -> DownloadedImportFile:
    """Скачивает поток с проверкой каждого redirect и фактического размера."""
    current = validate_public_url(url)
    spool = SpooledTemporaryFile(max_size=1024 * 1024)
    try:
        async with asyncio.timeout(timeout_seconds):
            async with httpcore.AsyncConnectionPool(
                network_backend=PublicNetworkBackend(), max_connections=1
            ) as pool:
                for redirect in range(6):
                    async with pool.stream(
                        "GET",
                        current,
                        headers=[
                            (b"accept-encoding", b"identity"),
                            (b"user-agent", b"DNK-Catalog-Import/1"),
                        ],
                        extensions={
                            "timeout": {
                                "connect": 15.0,
                                "read": 30.0,
                                "write": 30.0,
                                "pool": 15.0,
                            }
                        },
                    ) as response:
                        headers = {k.lower(): v for k, v in response.headers}
                        if response.status in {301, 302, 303, 307, 308}:
                            location = headers.get(b"location")
                            if location is None or redirect == 5:
                                raise InvalidCatalogValueError(
                                    "Слишком много перенаправлений источника."
                                )
                            current = validate_public_url(
                                urljoin(current, location.decode("latin-1"))
                            )
                            continue
                        if response.status != 200:
                            raise InvalidCatalogValueError(
                                f"Сервер источника вернул HTTP {response.status}."
                            )
                        if headers.get(
                            b"content-encoding", b"identity"
                        ).lower() not in {b"identity", b""}:
                            raise InvalidCatalogValueError(
                                "Сжатые источники пока не поддерживаются."
                            )
                        size = 0
                        async for chunk in response.aiter_stream():
                            size += len(chunk)
                            if size > limit:
                                raise InvalidCatalogValueError(
                                    "Превышен допустимый размер скачиваемого файла."
                                )
                            spool.write(chunk)
                        if not size:
                            raise InvalidCatalogValueError("Источник пуст.")
                        spool.seek(0)
                        return DownloadedImportFile(
                            spool,
                            size,
                            headers.get(b"content-type", b"application/octet-stream")
                            .decode("latin-1")
                            .split(";", 1)[0],
                        )
        raise InvalidCatalogValueError("Источник недоступен.")
    except BaseException:
        spool.close()
        raise
