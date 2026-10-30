import asyncio
from urllib.parse import urlsplit, unquote

import httpx

from src.modules.channels.application.content_feed.contracts import MAX_FEED_BYTES
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.application.error import (
    ChannelInputError,
    VerificationFailure,
)
from src.modules.channels.infrastructure.http import PublicHttpsTransport
from src.modules.channels.infrastructure.platforms.url import normalize_endpoint


class HttpsFeedSource:
    """Переиспользует закрепление публичного IP, TLS и лимит общего HTTP transport."""

    def validate_url(self, url: str) -> str:
        """Разрешает секрет в query, запрещает внутренние адреса и рекурсию фидов."""
        try:
            parsed = urlsplit(url)
            normalize_endpoint("https://" + parsed.netloc)
            if (
                parsed.scheme != "https"
                or parsed.fragment
                or "\\" in url
                or any(ord(char) < 33 for char in url)
                or "/channels/content-feeds/" in unquote(parsed.path)
            ):
                raise ValueError
        except (ChannelInputError, ValueError):
            raise FeedBuildError("feed_source_url_invalid") from None
        return url

    async def fetch(self, url: str) -> bytes:
        """Читает весь ответ до возврата; не следует даже публичным перенаправлениям."""
        self.validate_url(url)
        try:
            async with asyncio.timeout(30):
                # Transport не следует redirect и не пишет секретный source URL в HTTPX INFO.
                async with PublicHttpsTransport() as transport:
                    request = httpx.Request(
                        "GET",
                        url,
                        headers={"Accept": "application/xml, text/xml"},
                        extensions={
                            "timeout": {
                                "connect": 10,
                                "read": 10,
                                "write": 10,
                                "pool": 10,
                            }
                        },
                    )
                    response = await transport.handle_async_request(request)
            if response.status_code != 200:
                raise FeedBuildError("feed_source_unavailable", unavailable=True)
            data = response.content
            if not data or len(data) > MAX_FEED_BYTES:
                raise FeedBuildError(
                    "feed_source_empty" if not data else "feed_document_too_large"
                )
            return data
        except (httpx.HTTPError, OSError, TimeoutError, VerificationFailure):
            raise FeedBuildError("feed_source_unavailable", unavailable=True) from None
