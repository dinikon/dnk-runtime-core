from fastapi.responses import StreamingResponse


class PublicationImportImageResponse(StreamingResponse):
    """HTTP-поток одного авторизованного изображения предпросмотра."""
