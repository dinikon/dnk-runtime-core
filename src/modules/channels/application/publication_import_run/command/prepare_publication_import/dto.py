from dataclasses import dataclass
from src.modules.channels.application.publication_import_run.port.source import (
    PublicationSourceConnection,
)


@dataclass(frozen=True, slots=True)
class PreparePublicationImportResultDTO:
    """Передаёт готовые параметры внешнего чтения после завершения транзакции."""

    connection: PublicationSourceConnection
    checkpoint: str
    pages: int
