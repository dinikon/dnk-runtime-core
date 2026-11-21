from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.enum.locale_fallback_mode import (
    LocaleFallbackMode,
)
from src.modules.feed_builder.domain.feed.value_object.locale_code import LocaleCodeVO
from src.modules.feed_builder.domain.feed.validation import sequence
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class LocaleFallbackPolicyVO:
    """Задаёт конечную явную цепочку локалей или отсутствие подстановки."""

    mode: LocaleFallbackMode = LocaleFallbackMode.NONE
    locales: tuple[LocaleCodeVO, ...] = ()

    def __post_init__(self) -> None:
        """Проверяет режим, уникальность и согласованность состава цепочки."""
        locales = sequence(self.locales, label="Fallback locales", maximum=32)
        if not isinstance(self.mode, LocaleFallbackMode) or not all(
            isinstance(item, LocaleCodeVO) for item in locales
        ):
            raise InvalidFeedValueError("Нужны типизированные режим и локали fallback.")
        if len(set(locales)) != len(locales):
            raise InvalidFeedValueError("Локали fallback не должны повторяться.")
        if (self.mode == LocaleFallbackMode.LOCALE_CHAIN) != bool(locales):
            raise InvalidFeedValueError("Только LOCALE_CHAIN требует непустую цепочку.")
        object.__setattr__(self, "locales", locales)
