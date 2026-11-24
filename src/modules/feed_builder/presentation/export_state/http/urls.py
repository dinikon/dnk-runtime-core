from uuid import UUID

from fastapi import Request

from src.modules.shared.presentation.http.host import extract_request_host

PUBLIC_FEED_PREFIX = "/api/public/feed-builder"


def public_feed_url(request: Request, link_id: UUID, format_code: str) -> str:
    """Формирует HTTPS-ссылку для уже проверенного tenant-хоста."""
    return f"https://{extract_request_host(request)}{PUBLIC_FEED_PREFIX}/{link_id}/feed.{format_code}"
