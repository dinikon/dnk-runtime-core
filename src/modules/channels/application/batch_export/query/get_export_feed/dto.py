from dataclasses import dataclass
from src.modules.files.application.port.query_repository import FileContentLocationDTO


@dataclass(frozen=True, slots=True)
class GetExportFeedResultDTO:
    """Передаёт приватные координаты внешнему stream adapter без открытого SQL UoW."""

    location: FileContentLocationDTO
    digest: str
