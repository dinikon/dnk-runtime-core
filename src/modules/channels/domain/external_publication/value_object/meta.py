from dataclasses import dataclass
import json
from typing import Self
from src.modules.channels.domain.error import ChannelsValidationError
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


@dataclass(frozen=True, slots=True)
class PublicationMetaVO:
    """Хранит непрозрачные ядру данные плагина и общие диагностические коды."""

    provider_schema: str
    provider_json: str
    read_issues: tuple[str, ...]

    def __post_init__(self) -> None:
        """Проверяет общий envelope без знания контракта конкретной платформы."""
        try:
            if (
                not isinstance(self.provider_schema, str)
                or not self.provider_schema
                or len(self.provider_schema) > 100
            ):
                raise ValueError("invalid_schema")
            provider = json.loads(self.provider_json)
            if (
                not isinstance(provider, dict)
                or not isinstance(self.read_issues, tuple)
                or any(not isinstance(code, str) for code in self.read_issues)
            ):
                raise ValueError("invalid_meta")
            json.dumps(provider, allow_nan=False)
        except (ValueError, TypeError):
            raise ChannelsValidationError("invalid_publication_meta") from None

    @property
    def provider(self) -> dict[str, JsonValue]:
        """Возвращает копию данных плагина, исключая мутацию сохранённого VO."""
        return json.loads(self.provider_json)

    @classmethod
    def create(
        cls,
        provider_schema: str,
        provider: dict[str, JsonValue],
        read_issues: tuple[str, ...],
    ) -> Self:
        """Канонизирует безопасные данные, прошедшие схему плагина."""
        try:
            encoded = json.dumps(
                provider, sort_keys=True, ensure_ascii=False, allow_nan=False
            )
        except (TypeError, ValueError):
            raise ChannelsValidationError("invalid_publication_meta") from None
        return cls(provider_schema, encoded, read_issues)

    def to_document(self) -> dict[str, JsonValue]:
        """Возвращает независимое JSON-представление метаданных."""
        return {
            "schema_version": 1,
            "provider_schema": self.provider_schema,
            "provider": self.provider,
            "read_issues": list(self.read_issues),
        }

    @classmethod
    def from_document(cls, document: dict[str, JsonValue]) -> Self:
        """Восстанавливает известную версию envelope."""
        try:
            if (
                type(document["schema_version"]) is not int
                or document["schema_version"] != 1
                or not isinstance(document["read_issues"], list)
            ):
                raise ValueError("unsupported_version")
            return cls.create(
                document["provider_schema"],
                document["provider"],
                tuple(document["read_issues"]),
            )
        except (KeyError, TypeError, ValueError):
            raise ChannelsValidationError("invalid_publication_meta") from None
