from fastapi import Response
from src.modules.channels.application.content_feed.query.get_content_feed_xml.dto import (
    GetContentFeedXmlResultDTO,
)


class GetContentFeedXmlResponse(Response):
    """Отдаёт только полностью подготовленный документ с известной длиной."""

    media_type = "application/xml"

    def __init__(self, result: GetContentFeedXmlResultDTO) -> None:
        """Не выполняет SQL или сериализацию после начала HTTP-ответа."""
        super().__init__(
            content=result.document.content,
            media_type=self.media_type,
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            },
        )
