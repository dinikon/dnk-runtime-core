from src.modules.feed_builder.domain.feed.error import (
    InvalidPriceCalculationDefinitionError,
)


class CalculationDefinitionError(InvalidPriceCalculationDefinitionError):
    """Отклоняет неподдержанные зависимости и несовместимые семантические типы AST."""

    def __init__(
        self, code: str, message: str, *, path: tuple[str | int, ...] = ()
    ) -> None:
        """Сохраняет стабильный код и адрес ошибки определения."""
        super().__init__(message, path=path)
        self.code = code


class CalculationExecutionError(Exception):
    """Сообщает об ошибке фактически исполненной ветви без подстановки значения."""

    def __init__(self, code: str, message: str, path: tuple[str | int, ...]) -> None:
        """Сохраняет код, безопасное сообщение и путь выполненного узла."""
        super().__init__(message)
        self.code, self.path = code, path
