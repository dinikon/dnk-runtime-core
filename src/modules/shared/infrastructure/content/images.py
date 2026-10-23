"""Распознавание растровых изображений без декодирования и изменения содержимого."""

IMAGE_FILE_SUFFIXES: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/avif": "avif",
    "image/bmp": "bmp",
}
IMAGE_MIME_TYPES = frozenset(IMAGE_FILE_SUFFIXES)


def image_content_type(header: bytes) -> str | None:
    """Возвращает реальный MIME поддержанного raster-файла по ограниченному заголовку."""
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if (
        header[:2] == b"BM"
        and len(header) >= 18
        and int.from_bytes(header[14:18], "little")
        in (12, 16, 40, 52, 56, 64, 108, 124)
    ):
        return "image/bmp"
    if header[4:8] == b"ftyp":
        size = int.from_bytes(header[:4], "big")
        if 16 <= size <= len(header) and size % 4 == 0:
            brands = (header[8:12],) + tuple(
                header[offset : offset + 4] for offset in range(16, size, 4)
            )
            if any(brand in (b"avif", b"avis") for brand in brands):
                return "image/avif"
    return None
