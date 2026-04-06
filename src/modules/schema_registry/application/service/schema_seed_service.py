from __future__ import annotations

import re

from src.modules.schema_registry.application.ports.seed_reader import SeedReaderPort
from src.modules.schema_registry.domain.error import SeedValidationError
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.field.value_object.field_label import (
    FieldLabelVO,
)
from src.modules.schema_registry.domain.field.value_object.field_name import FieldNameVO
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class SchemaSeedService:

    def __init__(
        self,
        seed_reader: SeedReaderPort,
        field_type_catalog: FieldTypeCatalog,
    ) -> None:
        self._seed_reader = seed_reader
        self._field_type_catalog = field_type_catalog

    async def load(self, *, seed_path: str) -> SchemaSeed:
        seed = await self._seed_reader.read(seed_path=seed_path)
        self._validate(seed)
        return seed

    def _validate(self, seed: SchemaSeed) -> None:
        seen_singular_names: set[str] = set()
        seen_plural_names: set[str] = set()

        for object_seed in seed.objects:
            ObjectNameVO(
                singular=object_seed.singular_name,
                plural=object_seed.plural_name,
            )
            ObjectLabelVO(
                singular=object_seed.singular_label,
                plural=object_seed.plural_label,
            )

            if object_seed.singular_name in seen_singular_names:
                raise SeedValidationError(
                    f"Duplicate object singular_name '{object_seed.singular_name}'."
                )
            if object_seed.plural_name in seen_plural_names:
                raise SeedValidationError(
                    f"Duplicate object plural_name '{object_seed.plural_name}'."
                )

            seen_singular_names.add(object_seed.singular_name)
            seen_plural_names.add(object_seed.plural_name)

            field_names: set[str] = set()
            for field_seed in object_seed.fields:
                FieldNameVO(field_seed.name)
                FieldLabelVO(field_seed.label)
                self._field_type_catalog.from_seed_type(field_seed.type)
                if field_seed.name in field_names:
                    raise SeedValidationError(
                        f"Duplicate field '{field_seed.name}' "
                        f"in object '{object_seed.plural_name}'."
                    )
                field_names.add(field_seed.name)

            for index_seed in object_seed.indexes:
                self._validate_identifier(index_seed.name, "Index name")
                missing_fields = set(index_seed.fields) - field_names
                if missing_fields:
                    raise SeedValidationError(
                        f"Index '{index_seed.name}' references unknown fields "
                        f"{sorted(missing_fields)} in object '{object_seed.plural_name}'."
                    )

            for relation_seed in object_seed.relations:
                self._validate_identifier(relation_seed.name, "Relation name")
                if relation_seed.source_field not in field_names:
                    raise SeedValidationError(
                        f"Relation '{relation_seed.name}' references unknown source field "
                        f"'{relation_seed.source_field}' in object '{object_seed.plural_name}'."
                    )

                target_object = seed.get_object(relation_seed.target_object)
                if target_object is None:
                    raise SeedValidationError(
                        f"Relation '{relation_seed.name}' references unknown target object "
                        f"'{relation_seed.target_object}'."
                    )

                target_field_names = {
                    field_seed.name for field_seed in target_object.fields
                }
                if relation_seed.target_field not in target_field_names:
                    raise SeedValidationError(
                        f"Relation '{relation_seed.name}' references unknown target field "
                        f"'{relation_seed.target_field}' on object '{target_object.plural_name}'."
                    )

    @staticmethod
    def _validate_identifier(value: str, title: str) -> None:
        normalized = value.strip()
        if not normalized or not _IDENTIFIER_RE.fullmatch(normalized):
            raise SeedValidationError(
                f"{title} '{value}' must match ^[a-z][a-z0-9_]*$."
            )
