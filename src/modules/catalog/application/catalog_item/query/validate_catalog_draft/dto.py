from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidateCatalogDraftResultDTO:
    """Возвращает конкретный результат сценария validate_catalog_draft."""

    issues: tuple[tuple[str, str], ...]
    stock_status: str | None = None
