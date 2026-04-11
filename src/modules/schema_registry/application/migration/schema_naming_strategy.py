from __future__ import annotations

import re

from src.modules.schema_registry.domain.error import SeedValidationError

_PG_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class SchemaNamingStrategy:
    @classmethod
    def one_to_one_unique_index_name(
        cls,
        *,
        table_name: str,
        column_name: str,
    ) -> str:
        return cls._validate_identifier(
            f"{table_name}_{column_name}_one_to_one_uq",
            title="Generated one_to_one unique index name",
        )

    @staticmethod
    def validate_identifier(value: str, *, title: str) -> str:
        return SchemaNamingStrategy._validate_identifier(value, title=title)

    @staticmethod
    def _validate_identifier(value: str, *, title: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise SeedValidationError(f"{title} cannot be empty.")
        if len(normalized) > 63:
            raise SeedValidationError(
                f"{title} '{normalized}' is too long. "
                "PostgreSQL identifier max length is 63."
            )
        if not _PG_IDENTIFIER_RE.fullmatch(normalized):
            raise SeedValidationError(
                f"{title} '{value}' must match ^[a-z][a-z0-9_]*$."
            )
        return normalized
