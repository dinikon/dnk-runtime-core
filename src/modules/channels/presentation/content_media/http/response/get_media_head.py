from starlette.responses import Response
from src.modules.channels.application.content_media.query.get_media_content.dto import (
    GetMediaContentResultDTO,
)
from src.modules.channels.presentation.content_media.http.response.headers import (
    media_headers,
)


class GetMediaHeadResponse(Response):
    """Отдаёт метаданные доступного изображения без тела."""

    @classmethod
    def from_dto(cls, result: GetMediaContentResultDTO) -> "GetMediaHeadResponse":
        """Не открывает дополнительный поток для HEAD."""
        return cls(headers=media_headers(result))
