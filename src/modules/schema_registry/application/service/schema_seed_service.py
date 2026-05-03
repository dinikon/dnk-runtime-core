from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.application.migration.schema_naming_strategy import (
    SchemaNamingStrategy,
)
from src.modules.schema_registry.application.ports.seed_reader import SeedReaderPort
from src.modules.schema_registry.domain.error import SeedValidationError
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.field.value_object.field_label import (
    FieldLabelVO,
)
from src.modules.schema_registry.domain.field.value_object.field_name import FieldNameVO
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum
from src.modules.schema_registry.domain.seed.validated_schema_spec import (
    ValidatedFieldSpec,
    ValidatedIndexSpec,
    ValidatedObjectSpec,
    ValidatedRelationSpec,
    ValidatedSchemaSpec,
)


@dataclass(frozen=True, slots=True)
class _ObjectSeedPartial:
    """Промежуточное состояние object seed до валидации индексов и связей."""

    seed: ObjectSeed
    name: ObjectNameVO
    label: ObjectLabelVO
    kind: ObjectKind
    fields: tuple[ValidatedFieldSpec, ...]


class SchemaSeedService:
    """Загружает seed и нормализует его в валидированную runtime-спецификацию."""

    def __init__(
        self,
        seed_reader: SeedReaderPort,
        field_type_catalog: FieldTypeCatalog,
    ) -> None:
        """Инициализирует сервис reader-портом и каталогом поддержанных field-типов."""
        self._seed_reader = seed_reader
        self._field_type_catalog = field_type_catalog

    async def load(self, *, seed_path: str) -> ValidatedSchemaSpec:
        """Читает seed по пути и возвращает нормализованную спецификацию."""
        seed = await self._seed_reader.read(seed_path=seed_path)
        return self._normalize(seed)

    def _normalize(self, seed: SchemaSeed) -> ValidatedSchemaSpec:
        """Валидирует seed и приводит имена, типы, default, индексы и связи к spec.

        Нормализация проходит в два этапа: сначала собираются объекты и поля,
        чтобы построить lookup по singular/plural именам, затем валидируются
        индексы и relations, которым нужны ссылки на уже известные объекты.
        """
        seen_singular_names: set[str] = set()
        seen_plural_names: set[str] = set()
        global_index_names: set[str] = set()
        object_partials: list[_ObjectSeedPartial] = []
        objects_by_name: dict[
            str,
            tuple[ObjectNameVO, tuple[ValidatedFieldSpec, ...]],
        ] = {}

        for object_seed in seed.objects:
            object_name = ObjectNameVO(
                singular=object_seed.singular_name,
                plural=object_seed.plural_name,
            )
            object_label = ObjectLabelVO(
                singular=object_seed.singular_label,
                plural=object_seed.plural_label,
            )
            object_kind = self._normalize_object_kind(object_seed.kind)

            if object_name.singular in seen_singular_names:
                raise SeedValidationError(
                    f"Duplicate object singular_name '{object_name.singular}'."
                )
            if object_name.plural in seen_plural_names:
                raise SeedValidationError(
                    f"Duplicate object plural_name '{object_name.plural}'."
                )

            seen_singular_names.add(object_name.singular)
            seen_plural_names.add(object_name.plural)

            field_names: set[str] = set()
            field_specs: list[ValidatedFieldSpec] = []
            for field_seed in object_seed.fields:
                field_name = FieldNameVO(field_seed.name)
                field_label = FieldLabelVO(field_seed.label)
                field_type = self._field_type_catalog.from_seed_type(field_seed.type)
                field_kind = self._normalize_field_kind(field_seed.kind)
                if field_seed.options and not field_type.is_select_like():
                    raise SeedValidationError(
                        "Options are allowed only for select/multiselect fields."
                    )
                if field_name.value in field_names:
                    raise SeedValidationError(
                        f"Duplicate field '{field_name.value}' "
                        f"in object '{object_name.plural}'."
                    )
                field_names.add(field_name.value)
                field_specs.append(
                    ValidatedFieldSpec(
                        name=field_name.value,
                        type=field_seed.type.strip().lower(),
                        kind=field_kind,
                        field_type=field_type,
                        label=field_label.value,
                        description=field_seed.description.strip(),
                        is_nullable=field_seed.is_nullable,
                        default=self._normalize_default(field_seed.default),
                        options=dict(field_seed.options),
                        settings=dict(field_seed.settings),
                    )
                )

            normalized_fields = tuple(field_specs)
            object_partials.append(
                _ObjectSeedPartial(
                    seed=object_seed,
                    name=object_name,
                    label=object_label,
                    kind=object_kind,
                    fields=normalized_fields,
                )
            )
            objects_by_name[object_name.singular] = (object_name, normalized_fields)
            objects_by_name[object_name.plural] = (object_name, normalized_fields)

        objects: list[ValidatedObjectSpec] = []
        for partial in object_partials:
            object_seed = partial.seed
            object_name = partial.name
            object_label = partial.label
            object_kind = partial.kind
            normalized_fields = partial.fields
            field_names = {field_spec.name for field_spec in normalized_fields}
            indexes: list[ValidatedIndexSpec] = []

            for index_seed in object_seed.indexes:
                index_name = self._validate_identifier(index_seed.name, "Index name")
                index_fields = tuple(
                    field_name.strip() for field_name in index_seed.fields
                )
                if len(set(index_fields)) != len(index_fields):
                    raise SeedValidationError(
                        f"Index '{index_name}' contains duplicate fields."
                    )
                missing_fields = set(index_fields) - field_names
                if missing_fields:
                    raise SeedValidationError(
                        f"Index '{index_name}' references unknown fields "
                        f"{sorted(missing_fields)} in object '{object_name.plural}'."
                    )
                self._ensure_global_index_name_is_unique(
                    index_name=index_name,
                    global_index_names=global_index_names,
                )
                indexes.append(
                    ValidatedIndexSpec(
                        name=index_name,
                        fields=index_fields,
                        is_unique=index_seed.is_unique,
                    )
                )

            relations: list[ValidatedRelationSpec] = []
            for relation_seed in object_seed.relations:
                relation_name = self._validate_identifier(
                    relation_seed.name, "Relation name"
                )
                relation_type = self._normalize_relation_type(
                    relation_seed.relation_type
                )
                source_field = relation_seed.source_field.strip()
                if source_field not in field_names:
                    raise SeedValidationError(
                        f"Relation '{relation_name}' references unknown source field "
                        f"'{relation_seed.source_field}' "
                        f"in object '{object_name.plural}'."
                    )

                target_object = objects_by_name.get(relation_seed.target_object.strip())
                if target_object is None:
                    raise SeedValidationError(
                        f"Relation '{relation_name}' references unknown target object "
                        f"'{relation_seed.target_object}'."
                    )

                target_object_name, target_fields = target_object
                target_field_names = {field.name for field in target_fields}
                target_field = relation_seed.target_field.strip()
                if target_field not in target_field_names:
                    raise SeedValidationError(
                        f"Relation '{relation_name}' references unknown target field "
                        f"'{relation_seed.target_field}' "
                        f"on object '{target_object_name.plural}'."
                    )

                unique_index_name = None
                if relation_type == RelationTypeEnum.ONE_TO_ONE:
                    unique_index_name = (
                        SchemaNamingStrategy.one_to_one_unique_index_name(
                            table_name=object_name.plural,
                            column_name=source_field,
                        )
                    )
                    self._ensure_global_index_name_is_unique(
                        index_name=unique_index_name,
                        global_index_names=global_index_names,
                    )
                    indexes.append(
                        ValidatedIndexSpec(
                            name=unique_index_name,
                            fields=(source_field,),
                            is_unique=True,
                            is_generated=True,
                        )
                    )

                relations.append(
                    ValidatedRelationSpec(
                        name=relation_name,
                        relation_type=relation_type,
                        source_field=source_field,
                        target_object=target_object_name.singular,
                        target_field=target_field,
                        on_delete=self._normalize_on_delete(relation_seed.on_delete),
                        unique_index_name=unique_index_name,
                    )
                )

            objects.append(
                ValidatedObjectSpec(
                    singular_name=object_name.singular,
                    plural_name=object_name.plural,
                    singular_label=object_label.singular,
                    plural_label=object_label.plural,
                    description=object_seed.description.strip(),
                    kind=object_kind,
                    fields=normalized_fields,
                    indexes=tuple(indexes),
                    relations=tuple(relations),
                )
            )

        return ValidatedSchemaSpec(
            version=seed.version,
            code=seed.code.strip(),
            label=seed.label.strip(),
            objects=tuple(objects),
        )

    @staticmethod
    def _validate_identifier(value: str, title: str) -> str:
        """Делегирует валидацию PostgreSQL-идентификатора общей naming-стратегии."""
        return SchemaNamingStrategy.validate_identifier(value, title=title)

    @staticmethod
    def _normalize_relation_type(raw_type: str | RelationTypeEnum) -> RelationTypeEnum:
        """Валидирует тип связи seed и ограничивает его supported MVP-вариантами."""
        normalized = str(
            raw_type.value if isinstance(raw_type, RelationTypeEnum) else raw_type
        )
        normalized = normalized.strip().lower()
        try:
            relation_type = RelationTypeEnum(normalized)
        except ValueError as exc:
            raise SeedValidationError(
                f"Unsupported relation_type '{raw_type}'."
            ) from exc
        if not relation_type.is_source_owned_fk():
            raise SeedValidationError(
                f"Unsupported relation_type '{relation_type.value}' for MVP."
            )
        return relation_type

    @staticmethod
    def _normalize_on_delete(value: str) -> str:
        """Приводит on_delete из seed к каноническому lowercase-значению."""
        mapping = {
            "restrict": "restrict",
            "cascade": "cascade",
            "set null": "set null",
            "set_null": "set null",
            "no action": "no action",
            "no_action": "no action",
        }
        normalized = value.strip().lower()
        try:
            return mapping[normalized]
        except KeyError as exc:
            raise SeedValidationError(
                f"Unsupported relation on_delete '{value}'."
            ) from exc

    @staticmethod
    def _normalize_default(value: str | None) -> str | None:
        """Trim-ит default-значение seed и превращает пустую строку в None."""
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_object_kind(value: str | ObjectKind) -> ObjectKind:
        """Валидирует и нормализует kind runtime-объекта из seed."""
        try:
            return ObjectKind.from_value(value)
        except ValueError as exc:
            raise SeedValidationError(f"Unsupported object kind '{value}'.") from exc

    @staticmethod
    def _normalize_field_kind(value: str | FieldKind) -> FieldKind:
        """Валидирует и нормализует kind runtime-поля из seed."""
        try:
            return FieldKind.from_value(value)
        except ValueError as exc:
            raise SeedValidationError(f"Unsupported field kind '{value}'.") from exc

    @staticmethod
    def _ensure_global_index_name_is_unique(
        *,
        index_name: str,
        global_index_names: set[str],
    ) -> None:
        """Гарантирует уникальность имен индексов в пределах всей tenant-схемы."""
        if index_name in global_index_names:
            raise SeedValidationError(
                f"Duplicate index name '{index_name}' in schema seed."
            )
        global_index_names.add(index_name)
