from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from src.modules.runtime_data.domain.error import (
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)


@dataclass(frozen=True, slots=True)
class RuntimeFieldTypeDefinition:
    """Описывает соответствие metadata-типа Python и PostgreSQL представлениям."""

    metadata_type: str
    python_canonical: str
    postgres_canonical: str


class RuntimeFieldTypePolicy:
    """Проверяет и нормализует runtime payload согласно descriptor metadata."""

    IMMUTABLE_PATCH_FIELDS = frozenset({"id", "created_at", "updated_at"})

    _TYPE_TABLE: dict[str, RuntimeFieldTypeDefinition] = {
        "uuid": RuntimeFieldTypeDefinition("uuid", "UUID", "uuid"),
        "reference": RuntimeFieldTypeDefinition("reference", "UUID", "uuid"),
        "text": RuntimeFieldTypeDefinition("text", "str", "text"),
        "select": RuntimeFieldTypeDefinition("select", "str", "text"),
        "int": RuntimeFieldTypeDefinition("int", "int", "integer"),
        "decimal": RuntimeFieldTypeDefinition("decimal", "Decimal", "numeric(14,2)"),
        "bool": RuntimeFieldTypeDefinition("bool", "bool", "boolean"),
        "date": RuntimeFieldTypeDefinition("date", "date", "date"),
        "datetime": RuntimeFieldTypeDefinition(
            "datetime",
            "datetime(UTC-aware)",
            "timestamp without time zone",
        ),
        "json": RuntimeFieldTypeDefinition("json", "dict[str, Any]", "jsonb"),
        "multiselect": RuntimeFieldTypeDefinition("multiselect", "list[str]", "jsonb"),
    }

    def type_definition(self, type_code: str) -> RuntimeFieldTypeDefinition:
        """Возвращает определение поддержанного runtime-типа по его коду."""
        normalized = type_code.strip().lower()
        try:
            return self._TYPE_TABLE[normalized]
        except KeyError as exc:
            raise RuntimeDataPolicyError(
                f"Unsupported runtime metadata type '{type_code}'."
            ) from exc

    def coerce_insert_payload(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Нормализует insert payload и проверяет обязательные поля descriptor.

        Значения приводятся к canonical Python-типам до передачи gateway в БД.
        Nullable и default-поля могут отсутствовать, остальные поля обязательны.
        """
        fields_by_name = descriptor.fields_by_name
        self._validate_payload_keys(payload=payload, fields_by_name=fields_by_name)

        coerced_payload: dict[str, Any] = {}
        for field_name, raw_value in payload.items():
            field = fields_by_name[field_name]
            coerced_payload[field_name] = self._coerce_field_value(
                field=field,
                raw_value=raw_value,
            )

        for field in descriptor.fields:
            if field.name in coerced_payload:
                continue
            if field.is_nullable:
                continue
            if field.default_value is not None:
                continue
            raise RuntimeDataValidationError(
                f"Missing required field '{field.name}' for insert."
            )

        return coerced_payload

    def coerce_patch_payload(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        patch: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Нормализует patch payload и запрещает изменение immutable-полей."""
        fields_by_name = descriptor.fields_by_name
        self._validate_payload_keys(payload=patch, fields_by_name=fields_by_name)

        coerced_patch: dict[str, Any] = {}
        for field_name, raw_value in patch.items():
            if field_name in self.IMMUTABLE_PATCH_FIELDS:
                raise RuntimeDataValidationError(
                    f"Field '{field_name}' is immutable and cannot be updated."
                )
            field = fields_by_name[field_name]
            if field.kind.strip().lower() == "system":
                raise RuntimeDataValidationError(
                    f"Field '{field_name}' is system and cannot be updated."
                )
            coerced_patch[field_name] = self._coerce_field_value(
                field=field,
                raw_value=raw_value,
            )

        return coerced_patch

    def normalize_row(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        row: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Приводит строку из БД к runtime-формату, включая UTC-aware datetime."""
        normalized = dict(row)
        for field in descriptor.fields:
            if field.name not in normalized:
                continue
            value = normalized[field.name]
            if value is None:
                continue
            if field.type_code == "datetime" and isinstance(value, datetime):
                if value.tzinfo is None:
                    normalized[field.name] = value.replace(tzinfo=UTC)
                else:
                    normalized[field.name] = value.astimezone(UTC)
        return normalized

    @staticmethod
    def _validate_payload_keys(
        *,
        payload: Mapping[str, Any],
        fields_by_name: Mapping[str, RuntimeFieldDescriptor],
    ) -> None:
        """Проверяет, что payload не содержит полей вне descriptor."""
        unknown_fields = sorted(set(payload) - set(fields_by_name))
        if unknown_fields:
            raise RuntimeDataValidationError(
                f"Unknown payload fields: {unknown_fields}."
            )

    def _coerce_field_value(
        self,
        *,
        field: RuntimeFieldDescriptor,
        raw_value: Any,
    ) -> Any:
        """Приводит одно значение к типу поля и проверяет nullable/options правила."""
        if raw_value is None:
            if field.is_nullable:
                return None
            raise RuntimeDataValidationError(
                f"Field '{field.name}' is required and cannot be null."
            )

        if (
            isinstance(raw_value, str)
            and raw_value == ""
            and field.type_code != "text"
            and field.type_code != "select"
        ):
            raise RuntimeDataValidationError(
                f"Field '{field.name}' does not allow empty string values."
            )

        type_code = field.type_code
        self.type_definition(type_code)

        if type_code in {"uuid", "reference"}:
            return self._coerce_uuid(field_name=field.name, raw_value=raw_value)
        if type_code in {"text", "select"}:
            value = self._coerce_str(field_name=field.name, raw_value=raw_value)
            if type_code == "select" and field.options and value not in field.options:
                raise RuntimeDataValidationError(
                    f"Field '{field.name}' has unsupported option '{value}'."
                )
            return value
        if type_code == "int":
            return self._coerce_int(field_name=field.name, raw_value=raw_value)
        if type_code == "decimal":
            return self._coerce_decimal(field_name=field.name, raw_value=raw_value)
        if type_code == "bool":
            return self._coerce_bool(field_name=field.name, raw_value=raw_value)
        if type_code == "date":
            return self._coerce_date(field_name=field.name, raw_value=raw_value)
        if type_code == "datetime":
            return self._coerce_datetime(field_name=field.name, raw_value=raw_value)
        if type_code == "json":
            if not isinstance(raw_value, dict):
                raise RuntimeDataValidationError(
                    f"Field '{field.name}' requires a JSON object (dict)."
                )
            return dict(raw_value)
        if type_code == "multiselect":
            if not isinstance(raw_value, list) or not all(
                isinstance(item, str) for item in raw_value
            ):
                raise RuntimeDataValidationError(
                    f"Field '{field.name}' requires a list[str]."
                )
            values = list(raw_value)
            if field.options:
                for value in values:
                    if value not in field.options:
                        raise RuntimeDataValidationError(
                            f"Field '{field.name}' has unsupported option '{value}'."
                        )
            return list(dict.fromkeys(values))

        raise RuntimeDataPolicyError(
            f"Unsupported runtime metadata type '{type_code}'."
        )

    def coerce_value_for_field(
        self,
        *,
        field: RuntimeFieldDescriptor,
        raw_value: Any,
    ) -> Any:
        """Публичный helper для приведения значения под конкретное поле descriptor."""
        return self._coerce_field_value(field=field, raw_value=raw_value)

    @staticmethod
    def _coerce_uuid(*, field_name: str, raw_value: Any) -> UUID:
        """Приводит UUID-значение из UUID или строки."""
        if isinstance(raw_value, UUID):
            return raw_value
        if isinstance(raw_value, str):
            try:
                return UUID(raw_value)
            except ValueError as exc:
                raise RuntimeDataValidationError(
                    f"Field '{field_name}' has invalid UUID value."
                ) from exc
        raise RuntimeDataValidationError(
            f"Field '{field_name}' requires UUID or UUID string."
        )

    @staticmethod
    def _coerce_str(*, field_name: str, raw_value: Any) -> str:
        """Проверяет, что значение является строкой."""
        if isinstance(raw_value, str):
            return raw_value
        raise RuntimeDataValidationError(f"Field '{field_name}' requires string value.")

    @staticmethod
    def _coerce_int(*, field_name: str, raw_value: Any) -> int:
        """Приводит integer из int или строки, не принимая bool."""
        if isinstance(raw_value, bool):
            raise RuntimeDataValidationError(
                f"Field '{field_name}' requires integer value."
            )
        if isinstance(raw_value, int):
            return raw_value
        if isinstance(raw_value, str):
            try:
                return int(raw_value)
            except ValueError as exc:
                raise RuntimeDataValidationError(
                    f"Field '{field_name}' has invalid integer value."
                ) from exc
        raise RuntimeDataValidationError(
            f"Field '{field_name}' requires integer value."
        )

    @staticmethod
    def _coerce_decimal(*, field_name: str, raw_value: Any) -> Decimal:
        """Приводит Decimal из Decimal, int или строки и отклоняет float."""
        if isinstance(raw_value, float):
            raise RuntimeDataValidationError(
                f"Field '{field_name}' rejects float values; use Decimal or string."
            )
        if isinstance(raw_value, Decimal):
            return raw_value
        if isinstance(raw_value, int):
            return Decimal(raw_value)
        if isinstance(raw_value, str):
            try:
                return Decimal(raw_value)
            except InvalidOperation as exc:
                raise RuntimeDataValidationError(
                    f"Field '{field_name}' has invalid decimal value."
                ) from exc
        raise RuntimeDataValidationError(
            f"Field '{field_name}' requires Decimal/int/string value."
        )

    @staticmethod
    def _coerce_bool(*, field_name: str, raw_value: Any) -> bool:
        """Приводит boolean из bool или ограниченного набора строк."""
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, str):
            normalized = raw_value.strip().lower()
            if normalized in {"true", "1"}:
                return True
            if normalized in {"false", "0"}:
                return False
        raise RuntimeDataValidationError(
            f"Field '{field_name}' requires boolean value."
        )

    @staticmethod
    def _coerce_date(*, field_name: str, raw_value: Any) -> date:
        """Приводит date из date или ISO date строки."""
        if isinstance(raw_value, date) and not isinstance(raw_value, datetime):
            return raw_value
        if isinstance(raw_value, str):
            try:
                return date.fromisoformat(raw_value)
            except ValueError as exc:
                raise RuntimeDataValidationError(
                    f"Field '{field_name}' has invalid date value."
                ) from exc
        raise RuntimeDataValidationError(
            f"Field '{field_name}' requires date or ISO date string."
        )

    @staticmethod
    def _coerce_datetime(*, field_name: str, raw_value: Any) -> datetime:
        """Приводит datetime к UTC и снимает tzinfo для PostgreSQL timestamp."""
        value = raw_value
        if isinstance(value, str):
            iso = value.replace("Z", "+00:00")
            try:
                value = datetime.fromisoformat(iso)
            except ValueError as exc:
                raise RuntimeDataValidationError(
                    f"Field '{field_name}' has invalid datetime value."
                ) from exc

        if not isinstance(value, datetime):
            raise RuntimeDataValidationError(
                f"Field '{field_name}' requires datetime or ISO datetime string."
            )

        if value.tzinfo is None:
            aware = value.replace(tzinfo=UTC)
        else:
            aware = value.astimezone(UTC)

        return aware.replace(tzinfo=None)
