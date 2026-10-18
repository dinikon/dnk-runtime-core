from dataclasses import dataclass
import re
from typing import Self
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ContentBlock:
    """Определение блока внутри схемы ProductType без самостоятельного repository."""

    id: EntityIdVO
    code: str
    value_type: str
    required: bool
    position: int
    labels: dict[str, str]

    @classmethod
    def create(
        cls,
        identifier: EntityIdVO,
        code: str,
        value_type: str,
        required: bool,
        position: int,
        labels: dict[str, str],
    ) -> Self:
        """Создаёт блок с явным UUID и проверяет его определение."""
        return cls.restore(identifier, code, value_type, required, position, labels)

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        code: str,
        value_type: str,
        required: bool,
        position: int,
        labels: dict[str, str],
    ) -> Self:
        """Восстанавливает корректное определение блока и копирует переводы."""
        if (
            not isinstance(identifier, EntityIdVO)
            or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code)
            or value_type not in {"text", "rich_text"}
            or type(required) is not bool
            or type(position) is not int
            or position < 0
        ):
            raise InvalidCatalogValueError("Некорректное определение блока.")
        for locale, label in labels.items():
            LocaleVO(locale)
            if not isinstance(label, str) or not 1 <= len(label.strip()) <= 255:
                raise InvalidCatalogValueError("Некорректная подпись блока.")
        return cls(identifier, code, value_type, required, position, dict(labels))
