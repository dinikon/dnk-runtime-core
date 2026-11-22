from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SetPublicationOverrideResultDTO:
    """Возвращает версию публикации после изменения ручного значения."""

    publication_version: int
