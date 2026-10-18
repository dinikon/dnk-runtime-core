from enum import StrEnum


class FileCategory(StrEnum):
    """Категории проекций файлового менеджера, независимые от состояния агрегата."""

    DOCUMENTS = "documents"
    IMAGES = "images"
    VIDEOS = "videos"
    OTHER = "other"


DOCUMENT_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "text/plain",
        "text/csv",
        "text/html",
        "text/markdown",
        "text/xml",
        "application/xml",
        "text/rtf",
        "application/rtf",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.oasis.opendocument.text",
        "application/vnd.oasis.opendocument.spreadsheet",
        "application/vnd.oasis.opendocument.presentation",
        "application/vnd.ms-word.document.macroenabled.12",
        "application/vnd.ms-excel.sheet.macroenabled.12",
        "application/vnd.ms-powerpoint.presentation.macroenabled.12",
    }
)


def classify_file(content_type: str) -> FileCategory:
    """Классифицирует MIME без регистра, внешних пробелов и параметров."""
    mime = content_type.partition(";")[0].strip().lower()
    if mime.startswith("image/"):
        return FileCategory.IMAGES
    if mime.startswith("video/"):
        return FileCategory.VIDEOS
    if mime in DOCUMENT_MIME_TYPES:
        return FileCategory.DOCUMENTS
    return FileCategory.OTHER
