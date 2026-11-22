from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResetPublicationOverrideResultDTO:
    """Возвращает версию публикации после изменения ручного значения."""

    publication_version: int
