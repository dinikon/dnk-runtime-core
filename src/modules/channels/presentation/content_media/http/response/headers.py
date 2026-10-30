from src.modules.channels.application.content_media.query.get_media_content.dto import (
    GetMediaContentResultDTO,
)


def media_headers(result: GetMediaContentResultDTO) -> dict[str, str]:
    """Не раскрывает исходное имя, storage coordinates и токены в заголовках."""
    return {
        "Content-Type": result.content_type,
        "Content-Length": str(result.size_bytes),
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": "inline",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "sandbox; default-src 'none'",
    }
