from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)


class CatalogImportConcurrencyPolicy:
    """Ограничивает число одновременно активных импортов одного рабочего пространства."""

    def __init__(self, maximum: int) -> None:
        """Принимает положительный лимит, независимо от способа его настройки."""
        if type(maximum) is not int or maximum < 1:
            raise InvalidCatalogValueError(
                "Лимит активных импортов должен быть положительным целым числом."
            )
        self.maximum = maximum

    def ensure_capacity(self, active: int) -> None:
        """Отклоняет новый запуск, когда все доступные места уже заняты."""
        if active >= self.maximum:
            raise CatalogConflictError(
                f"Достигнут лимит одновременных импортов в рабочем пространстве: {self.maximum}. "
                "Дождитесь завершения или остановите один из активных импортов."
            )
