from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation

from src.modules.schema_registry.domain.field.enum.field_type import FieldTypeEnum
from src.modules.schema_registry.domain.field.enum.sql_type_preset import (
    SqlTypePresetEnum,
)
from src.modules.schema_registry.domain.field.value_object.field_type import FieldTypeVO
from src.modules.schema_registry.domain.error import (
    SeedValidationError,
    UnsupportedSchemaChangeError,
)

_POSTGRES_TYPE_CAST_RE = re.compile(r"^(?P<value>.+?)::[\w\s\[\]\.]+$")


class FieldTypeService:

    @staticmethod
    def from_seed_type(raw_type: str) -> FieldTypeVO:
        normalized = raw_type.strip().lower()

        mapping = {
            FieldTypeEnum.UUID.value: FieldTypeVO.sql(
                FieldTypeEnum.UUID,
                SqlTypePresetEnum.UUID,
            ),
            FieldTypeEnum.TEXT.value: FieldTypeVO.sql(
                FieldTypeEnum.TEXT,
                SqlTypePresetEnum.TEXT,
            ),
            FieldTypeEnum.INT.value: FieldTypeVO.sql(
                FieldTypeEnum.INT,
                SqlTypePresetEnum.INTEGER,
            ),
            FieldTypeEnum.DECIMAL.value: FieldTypeVO.sql(
                FieldTypeEnum.DECIMAL,
                SqlTypePresetEnum.NUMERIC_14_2,
            ),
            FieldTypeEnum.BOOL.value: FieldTypeVO.sql(
                FieldTypeEnum.BOOL,
                SqlTypePresetEnum.BOOLEAN,
            ),
            FieldTypeEnum.DATE.value: FieldTypeVO.sql(
                FieldTypeEnum.DATE,
                SqlTypePresetEnum.DATE,
            ),
            FieldTypeEnum.DATETIME.value: FieldTypeVO.sql(
                FieldTypeEnum.DATETIME,
                SqlTypePresetEnum.TIMESTAMP,
            ),
            FieldTypeEnum.JSON.value: FieldTypeVO.sql(
                FieldTypeEnum.JSON,
                SqlTypePresetEnum.JSONB,
            ),
            FieldTypeEnum.SELECT.value: FieldTypeVO.sql(
                FieldTypeEnum.SELECT,
                SqlTypePresetEnum.TEXT,
            ),
            FieldTypeEnum.MULTISELECT.value: FieldTypeVO.sql(
                FieldTypeEnum.MULTISELECT,
                SqlTypePresetEnum.JSONB,
            ),
        }

        try:
            return mapping[normalized]
        except KeyError as exc:
            raise SeedValidationError(
                f"Unsupported seed field type '{raw_type}'."
            ) from exc

    def sql_preset_from_seed_type(self, raw_type: str) -> SqlTypePresetEnum:
        field_type = self.from_seed_type(raw_type)
        if field_type.sql_preset is None:
            raise SeedValidationError(
                f"Seed field type '{raw_type}' has no SQL preset."
            )
        return field_type.sql_preset

    @staticmethod
    def sql_preset_from_postgres_type(format_type: str) -> SqlTypePresetEnum:
        normalized = format_type.strip().lower()
        mapping = {
            "uuid": SqlTypePresetEnum.UUID,
            "text": SqlTypePresetEnum.TEXT,
            "character varying(255)": SqlTypePresetEnum.VARCHAR_255,
            "varchar(255)": SqlTypePresetEnum.VARCHAR_255,
            "integer": SqlTypePresetEnum.INTEGER,
            "bigint": SqlTypePresetEnum.BIGINT,
            "numeric(14,2)": SqlTypePresetEnum.NUMERIC_14_2,
            "boolean": SqlTypePresetEnum.BOOLEAN,
            "date": SqlTypePresetEnum.DATE,
            "timestamp without time zone": SqlTypePresetEnum.TIMESTAMP,
            "jsonb": SqlTypePresetEnum.JSONB,
        }
        try:
            return mapping[normalized]
        except KeyError as exc:
            raise UnsupportedSchemaChangeError(
                f"Unsupported PostgreSQL column type '{format_type}'."
            ) from exc

    @staticmethod
    def render_sql_preset(sql_preset: SqlTypePresetEnum) -> str:
        mapping = {
            SqlTypePresetEnum.UUID: "uuid",
            SqlTypePresetEnum.TEXT: "text",
            SqlTypePresetEnum.VARCHAR_255: "varchar(255)",
            SqlTypePresetEnum.INTEGER: "integer",
            SqlTypePresetEnum.BIGINT: "bigint",
            SqlTypePresetEnum.NUMERIC_14_2: "numeric(14,2)",
            SqlTypePresetEnum.BOOLEAN: "boolean",
            SqlTypePresetEnum.DATE: "date",
            SqlTypePresetEnum.TIMESTAMP: "timestamp without time zone",
            SqlTypePresetEnum.JSONB: "jsonb",
        }
        return mapping[sql_preset]

    def normalize_seed_default(
        self,
        *,
        raw_default: str | None,
        sql_preset: SqlTypePresetEnum,
    ) -> str | None:
        try:
            return self._normalize_default(
                raw_default=raw_default, sql_preset=sql_preset
            )
        except UnsupportedSchemaChangeError as exc:
            raise SeedValidationError(str(exc)) from exc

    def normalize_postgres_default(
        self,
        *,
        raw_default: str | None,
        sql_preset: SqlTypePresetEnum,
    ) -> str | None:
        return self._normalize_default(raw_default=raw_default, sql_preset=sql_preset)

    def _normalize_default(
        self,
        *,
        raw_default: str | None,
        sql_preset: SqlTypePresetEnum,
    ) -> str | None:
        if raw_default is None:
            return None

        value = raw_default.strip()
        if not value:
            return None

        value = self._strip_outer_parentheses(value)
        value = self._strip_postgres_casts(value)
        lowered = value.lower()

        if sql_preset == SqlTypePresetEnum.TIMESTAMP and lowered in {
            "now()",
            "current_timestamp",
        }:
            return "CURRENT_TIMESTAMP"

        if sql_preset in {SqlTypePresetEnum.TEXT, SqlTypePresetEnum.VARCHAR_255}:
            return self._quote_sql_string(self._extract_literal(value))

        if sql_preset == SqlTypePresetEnum.UUID:
            return f"{self._quote_sql_string(self._extract_literal(value))}::uuid"

        if sql_preset == SqlTypePresetEnum.DATE:
            return f"{self._quote_sql_string(self._extract_literal(value))}::date"

        if sql_preset == SqlTypePresetEnum.TIMESTAMP:
            return (
                f"{self._quote_sql_string(self._extract_literal(value))}"
                "::timestamp without time zone"
            )

        if sql_preset == SqlTypePresetEnum.BOOLEAN:
            if lowered in {"true", "false"}:
                return lowered
            if lowered in {"1", "'1'"}:
                return "true"
            if lowered in {"0", "'0'"}:
                return "false"
            raise UnsupportedSchemaChangeError(
                f"Unsupported boolean default '{raw_default}'."
            )

        if sql_preset in {SqlTypePresetEnum.INTEGER, SqlTypePresetEnum.BIGINT}:
            literal = self._extract_literal(value)
            try:
                return str(int(literal))
            except ValueError as exc:
                raise UnsupportedSchemaChangeError(
                    f"Unsupported integer default '{raw_default}'."
                ) from exc

        if sql_preset == SqlTypePresetEnum.NUMERIC_14_2:
            literal = self._extract_literal(value)
            try:
                decimal_value = Decimal(literal)
            except InvalidOperation as exc:
                raise UnsupportedSchemaChangeError(
                    f"Unsupported numeric default '{raw_default}'."
                ) from exc
            normalized = format(decimal_value.normalize(), "f")
            if "." in normalized:
                normalized = normalized.rstrip("0").rstrip(".")
            return normalized or "0"

        if sql_preset == SqlTypePresetEnum.JSONB:
            literal = self._extract_literal(value)
            try:
                payload = json.loads(literal)
            except json.JSONDecodeError as exc:
                raise UnsupportedSchemaChangeError(
                    f"Unsupported jsonb default '{raw_default}'."
                ) from exc
            serialized = json.dumps(
                payload,
                separators=(",", ":"),
                sort_keys=True,
            )
            return f"{self._quote_sql_string(serialized)}::jsonb"

        raise UnsupportedSchemaChangeError(
            f"Unsupported default normalization for SQL preset '{sql_preset.value}'."
        )

    @classmethod
    def _strip_outer_parentheses(cls, value: str) -> str:
        normalized = value.strip()
        while normalized.startswith("(") and normalized.endswith(")"):
            candidate = normalized[1:-1].strip()
            if not candidate:
                break
            normalized = candidate
        return normalized

    @classmethod
    def _strip_postgres_casts(cls, value: str) -> str:
        normalized = value.strip()
        while True:
            match = _POSTGRES_TYPE_CAST_RE.fullmatch(normalized)
            if match is None:
                return normalized
            normalized = cls._strip_outer_parentheses(match.group("value"))

    @staticmethod
    def _extract_literal(value: str) -> str:
        normalized = value.strip()
        if normalized.startswith("'") and normalized.endswith("'"):
            return normalized[1:-1].replace("''", "'")
        return normalized

    @staticmethod
    def _quote_sql_string(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"
