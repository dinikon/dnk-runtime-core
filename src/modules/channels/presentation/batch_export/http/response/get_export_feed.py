from fastapi.responses import StreamingResponse


class ExportFeedResponse(StreamingResponse):
    """HTTP поток одного подписанного immutable XML без доступа к Console."""
