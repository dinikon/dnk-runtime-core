from __future__ import annotations

import hashlib
import re

from src.modules.schema_registry.domain.error import SeedValidationError

_PG_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class SchemaNamingStrategy:
    """Централизует правила именования PostgreSQL-идентификаторов schema_registry."""

    @classmethod
    def primary_key_name(cls, *, table_name: str) -> str:
        """Генерирует имя primary key constraint для таблицы."""
        return cls._generated_identifier(
            f"pk_{table_name}",
            title="Generated primary key constraint name",
        )

    @classmethod
    def one_to_one_unique_index_name(
        cls,
        *,
        table_name: str,
        column_name: str,
    ) -> str:
        """Генерирует имя unique-индекса для one_to_one связи и валидирует его."""
        return cls._generated_identifier(
            f"uq_{table_name}_{column_name}",
            title="Generated one_to_one unique index name",
        )

    @classmethod
    def foreign_key_name(
        cls,
        *,
        source_table_name: str,
        source_column_name: str,
        target_table_name: str,
    ) -> str:
        """Генерирует имя FK constraint по canonical naming convention."""
        return cls._generated_identifier(
            f"fk_{source_table_name}_{source_column_name}_{target_table_name}",
            title="Generated foreign key name",
        )

    @classmethod
    def foreign_key_index_name(
        cls,
        *,
        table_name: str,
        column_name: str,
    ) -> str:
        """Генерирует имя индекса для FK-колонки."""
        return cls._generated_identifier(
            f"idx_{table_name}_{column_name}",
            title="Generated foreign key index name",
        )

    @classmethod
    def many_to_many_unique_index_name(
        cls,
        *,
        table_name: str,
        source_column_name: str,
        target_column_name: str,
    ) -> str:
        """Генерирует имя unique-индекса для пары join-колонок M2M."""
        return cls._generated_identifier(
            f"uq_{table_name}_{source_column_name}_{target_column_name}",
            title="Generated many_to_many unique index name",
        )

    @staticmethod
    def validate_identifier(value: str, *, title: str) -> str:
        """Валидирует внешний PostgreSQL-идентификатор и возвращает trim-значение."""
        return SchemaNamingStrategy._validate_identifier(value, title=title)

    @staticmethod
    def _validate_identifier(value: str, *, title: str) -> str:
        """Проверяет обязательность, длину и формат PostgreSQL-идентификатора."""
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

    @staticmethod
    def _generated_identifier(value: str, *, title: str) -> str:
        """Возвращает PostgreSQL-safe generated identifier с hash suffix при overflow."""
        normalized = value.strip()
        if len(normalized) > 63:
            digest = hashlib.blake2s(
                normalized.encode("utf-8"),
                digest_size=4,
            ).hexdigest()
            normalized = f"{normalized[:54]}_{digest}"
        return SchemaNamingStrategy._validate_identifier(normalized, title=title)
