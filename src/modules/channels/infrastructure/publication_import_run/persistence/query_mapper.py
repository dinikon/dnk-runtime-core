from typing import Any, Mapping
from src.modules.channels.application.publication_import_run.query.get_publication_import_run.dto import (
    PublicationImportRunDetailsDTO,
)


class PublicationImportQueryMapper:
    """Переводит готовую SQL-проекцию прогресса в DTO сценария чтения."""

    @staticmethod
    def to_details(row: Mapping[str, Any]) -> PublicationImportRunDetailsDTO:
        """Переносит поля проекции без восстановления агрегата и правил переходов."""
        return PublicationImportRunDetailsDTO(
            id=row["id"],
            channel_id=row["channel_id"],
            status=row["status"],
            pages=row["pages"],
            resources=row["resources"],
            error_code=row["error_code"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
