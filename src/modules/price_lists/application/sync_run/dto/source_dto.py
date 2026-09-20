from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class FetchResult:
    """Временный локальный источник и метаданные скачивания."""

    path: Path
    checksum: str
    content_type: str
    size: int
    etag: str | None = None
    last_modified: str | None = None


@dataclass(slots=True, frozen=True)
class SourceInspection:
    """Доступные листы, колонки и пути ограниченного preview."""

    sheets: tuple[str, ...] = ()
    columns: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()


__all__ = ["FetchResult", "SourceInspection"]
