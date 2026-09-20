from dataclasses import dataclass
from typing import Any
import re
from src.modules.price_lists.domain.price_list.error import PriceListValidationError
from src.modules.price_lists.domain.price_list.value_object.status import SourceFormat


def validate_source_config(source_format: str, config: dict[str, Any]) -> None:
    if source_format in {SourceFormat.XML.value, SourceFormat.YAML.value}:
        path = str(config.get("item_path") or "")
        parts = path.split(".") if path else []
        if (
            not parts
            or len(parts) > 64
            or any(
                not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_:-]*", part) for part in parts
            )
        ):
            raise PriceListValidationError("A valid item_path is required.")
    if source_format == SourceFormat.XLSX.value:
        sheet = str(config.get("sheet_name") or "")
        header_row = int(config.get("header_row", 1))
        data_start = int(config.get("data_start_row", header_row + 1))
        if not sheet or len(sheet) > 31:
            raise PriceListValidationError("A valid XLSX sheet_name is required.")
        if not 1 <= header_row <= 10_000 or not header_row < data_start <= 10_001:
            raise PriceListValidationError(
                "Invalid XLSX header/data row configuration."
            )


def validate_mapping_config(mapping: dict[str, Any]) -> None:
    allowed_fields = {
        "external_id",
        "sku",
        "title",
        "purchase_price",
        "rrp",
        "currency",
        "availability",
        "quantity",
    }
    unknown = set(mapping) - allowed_fields
    if unknown:
        raise PriceListValidationError("Mapping contains unsupported target fields.")
    for field in ("external_id", "sku", "title", "purchase_price", "currency"):
        specification = mapping.get(field)
        if not isinstance(specification, dict) or not (
            specification.get("selector") is not None
            or specification.get("selectors")
            or "constant" in specification
        ):
            raise PriceListValidationError(f"Mapping for {field} is required.")
    for specification in mapping.values():
        if not isinstance(specification, dict):
            raise PriceListValidationError("Mapping specifications must be objects.")
        selectors = specification.get("selectors") or [specification.get("selector")]
        if (
            not isinstance(selectors, (list, tuple))
            or len(selectors) > 5
            or any(
                selector is not None
                and (
                    isinstance(selector, bool)
                    or not isinstance(selector, (str, int))
                    or isinstance(selector, int)
                    and selector < 0
                    or isinstance(selector, str)
                    and not 1 <= len(selector) <= 255
                )
                for selector in selectors
            )
        ):
            raise PriceListValidationError("Mapping selector limit exceeded.")


@dataclass(slots=True, frozen=True)
class TitleVO:
    """Нормализованное название сущности прайс-листов."""

    value: str

    def __post_init__(self):
        if not isinstance(self.value, str) or not 1 <= len(self.value.strip()) <= 255:
            raise PriceListValidationError("Title must contain 1 to 255 characters.")
        object.__setattr__(self, "value", self.value.strip())


@dataclass(slots=True, frozen=True)
class SourceConfigurationVO:
    """Проверенная конфигурация выбора записей источника."""

    source_format: str
    value: dict[str, Any]

    def __post_init__(self):
        if self.source_format not in ("xml", "yaml", "xlsx"):
            raise PriceListValidationError("Unsupported source format.")
        if not isinstance(self.value, dict):
            raise PriceListValidationError("Source configuration must be an object.")
        try:
            validate_source_config(self.source_format, self.value)
        except (ValueError, TypeError):
            raise PriceListValidationError("Invalid source configuration.") from None


@dataclass(slots=True, frozen=True)
class MappingConfigurationVO:
    """Проверенный mapping полей предложения."""

    value: dict[str, Any]

    def __post_init__(self):
        if not isinstance(self.value, dict):
            raise PriceListValidationError("Mapping must be an object.")
        try:
            validate_mapping_config(self.value)
        except (ValueError, TypeError):
            raise PriceListValidationError("Invalid mapping configuration.") from None


@dataclass(slots=True, frozen=True)
class ScheduleVO:
    """Политики синхронизации и идентификатор календарного расписания."""

    cron_expression: str
    timezone: str
    new_item_policy: str = "create"
    missing_item_policy: str = "mark_out_of_stock"
    missing_threshold: int = 2

    def __post_init__(self):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        if (
            not isinstance(self.cron_expression, str)
            or not 5 <= len(self.cron_expression) <= 128
        ):
            raise PriceListValidationError("Invalid CRON expression.")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            raise PriceListValidationError("Unknown timezone.") from None
        if self.new_item_policy not in (
            "create",
            "ignore",
            "quarantine",
        ) or self.missing_item_policy not in (
            "mark_out_of_stock",
            "mark_missing",
            "keep_last",
            "archive",
        ):
            raise PriceListValidationError("Unknown synchronization policy.")
        if (
            type(self.missing_threshold) is not int
            or not 1 <= self.missing_threshold <= 100
        ):
            raise PriceListValidationError("Invalid missing threshold.")


__all__ = ["TitleVO", "SourceConfigurationVO", "MappingConfigurationVO", "ScheduleVO"]
