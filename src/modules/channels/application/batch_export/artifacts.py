from uuid import UUID, uuid5


def export_artifact_id(run_id: UUID) -> UUID:
    """Отделяет namespace серверного файла от переданного пользователем ID операции."""
    return uuid5(run_id, "channels:batch-export:xml:v1")
