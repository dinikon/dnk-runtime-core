from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.validation import text


@dataclass(frozen=True, slots=True)
class LocaleCodeVO:
    """Код локали без выбора языка или обращения к справочнику."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет лексическую форму тега и нормализует регистр его частей."""
        value = text(
            self.value,
            label="Locale",
            maximum=64,
            pattern=r"(?:[A-Za-z]{2,8}|[xXiI])(?:-[A-Za-z0-9]{1,8})*",
        )
        parts = value.split("-")
        if len(parts[0]) == 1 and len(parts) == 1:
            raise InvalidFeedValueError(
                "Однобуквенный префикс локали требует продолжения."
            )
        result = [parts[0].lower()]
        extension = len(parts[0]) == 1
        for part in parts[1:]:
            extension = extension or len(part) == 1
            if extension:
                result.append(part.lower())
            elif len(part) == 4 and part.isalpha():
                result.append(part.title())
            elif len(part) == 2 and part.isalpha():
                result.append(part.upper())
            else:
                result.append(part.lower())
        object.__setattr__(self, "value", "-".join(result))
