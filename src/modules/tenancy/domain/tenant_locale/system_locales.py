from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemLocale:
    """Доступная для выбора локаль системы."""

    code: str
    name: str


SYSTEM_LOCALES = (
    SystemLocale("uk", "Українська"),
    SystemLocale("en", "English"),
)
SYSTEM_LOCALE_CODES = frozenset(locale.code for locale in SYSTEM_LOCALES)
