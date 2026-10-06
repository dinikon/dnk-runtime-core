from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImportPublicationPageResultDTO:
    """Сообщает, была ли сохранена страница текущим владельцем запуска."""

    saved: bool
    completed: bool
