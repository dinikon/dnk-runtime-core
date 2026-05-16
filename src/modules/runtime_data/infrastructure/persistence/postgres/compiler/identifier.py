from __future__ import annotations

import re

from src.modules.runtime_data.domain import RuntimeDataPolicyError
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_identifier(value: str, title: str) -> None:
    """Validates a PostgreSQL identifier before dynamic SQL composition."""

    normalized = value.strip()
    if not _IDENTIFIER_RE.fullmatch(normalized):
        raise RuntimeDataPolicyError(f"Invalid {title} identifier '{value}'.")


def quote_identifier(identifier: str) -> str:
    """Quotes a PostgreSQL identifier after validation has happened."""

    return f'"{identifier}"'


def qualified_table(schema_name: str, table_name: str) -> str:
    """Returns a quoted PostgreSQL schema.table reference."""

    validate_identifier(schema_name, "schema_name")
    validate_identifier(table_name, "table_name")
    return f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"


def qualified_descriptor_table(descriptor: RuntimeObjectDescriptor) -> str:
    """Returns a quoted schema.table reference for a runtime descriptor."""

    return qualified_table(descriptor.schema_name, descriptor.table_name)


def ensure_descriptor_identifiers(descriptor: RuntimeObjectDescriptor) -> None:
    """Validates all identifiers used by descriptor-backed SQL."""

    validate_identifier(descriptor.schema_name, "schema_name")
    validate_identifier(descriptor.table_name, "table_name")
    validate_identifier(descriptor.pk, "primary key")
    for field in descriptor.fields:
        validate_identifier(field.name, "field")


__all__ = [
    "ensure_descriptor_identifiers",
    "qualified_descriptor_table",
    "qualified_table",
    "quote_identifier",
    "validate_identifier",
]
