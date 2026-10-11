from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetCurrencyValidationCatalogItemDTO:
    """Справочная запись для batch-проверки кодов и исключения металлов."""

    code: str
    numeric_code: str | None
    minor_units: int | None
    is_metal: bool


@dataclass(frozen=True, slots=True)
class GetCurrencyValidationCatalogResultDTO:
    """Возвращает активные записи и отсутствующие либо неактивные коды."""

    currencies: tuple[GetCurrencyValidationCatalogItemDTO, ...]
    missing_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GetCurrencyValidationCatalogRecordDTO:
    """Передаёт SQL-проекцию batch-сценария до доменной классификации."""

    code: str
    numeric_code: str | None
    minor_units: int | None
