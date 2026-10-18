from collections.abc import Mapping
from typing import Any
from uuid import UUID
from src.modules.channels.application.sync_run.query.get_publication_initialization.dto import (
    GetPublicationInitializationResultDTO,
)


class SyncRunQueryMapper:
    """Собирает прогресс и явное отсутствие запуска без Domain."""

    @staticmethod
    def to_details(
        connection_id: UUID,
        row: Mapping[str, Any] | None,
        recovery_required: bool = False,
    ) -> GetPublicationInitializationResultDTO:
        """Не выдаёт неполную загрузку за успешную и не выдумывает total."""
        if row is None:
            return GetPublicationInitializationResultDTO(
                None,
                connection_id,
                "not_started",
                0,
                0,
                0,
                None,
                (),
                None,
                None,
                False,
                False,
            )
        return GetPublicationInitializationResultDTO(
            row["id"],
            connection_id,
            row["status"],
            row["processed"],
            row["invalid"],
            row["sequence"],
            row["reason_code"],
            tuple(row["limitations"]),
            row["updated_at"],
            row["job_id"],
            row["read_complete"],
            recovery_required,
        )
