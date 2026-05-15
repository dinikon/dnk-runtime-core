from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.application.migration.schema_naming_strategy import (
    SchemaNamingStrategy,
)
from src.modules.schema_registry.application.ports.seed_reader import SeedReaderPort
from src.modules.schema_registry.domain.error import SeedValidationError
from src.modules.schema_registry.domain.field.enum.field_type import FieldTypeEnum
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
from src.modules.schema_registry.domain.object.naming import (
    has_custom_object_prefix,
    normalize_custom_object_names,
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
            object_kind = self._normalize_object_kind(object_seed.kind)
            singular_name = object_seed.singular_name
            plural_name = object_seed.plural_name
            if object_kind == ObjectKind.CUSTOM:
                singular_name, plural_name = normalize_custom_object_names(
                    singular_name=singular_name,
                    plural_name=plural_name,
                )
            object_name = ObjectNameVO(
                singular=singular_name,
                plural=plural_name,
            )
            object_label = ObjectLabelVO(
                singular=object_seed.singular_label,
                plural=object_seed.plural_label,
            )
            self._ensure_non_custom_object_does_not_use_custom_prefix(
                object_name=object_name,
                object_kind=object_kind,
            )

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

        indexes_by_object: dict[str, list[ValidatedIndexSpec]] = {}
        relations_by_source_object: dict[str, list[ValidatedRelationSpec]] = {}
        seen_relation_names: set[str] = set()

        for partial in object_partials:
            object_seed = partial.seed
            object_name = partial.name
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

            indexes_by_object[object_name.plural] = indexes
            relations_by_source_object[object_name.plural] = []

        for partial in object_partials:
            object_seed = partial.seed
            object_name = partial.name
            for relation_seed in object_seed.relations:
                relation_name = self._validate_identifier(
                    relation_seed.name, "Relation name"
                )
                if relation_name in seen_relation_names:
                    raise SeedValidationError(
                        f"Duplicate relation name '{relation_name}' in schema seed."
                    )
                seen_relation_names.add(relation_name)

                relation_type = self._normalize_relation_type(
                    relation_seed.relation_type
                )
                source_object_name, _ = self._require_object(
                    object_name=relation_seed.source_object,
                    objects_by_name=objects_by_name,
                    relation_name=relation_name,
                    role="source_object",
                )
                if source_object_name != object_name:
                    raise SeedValidationError(
                        f"Relation '{relation_name}' must be declared under "
                        f"its source object '{source_object_name.plural}'."
                    )
                target_object_name, _ = self._require_object(
                    object_name=relation_seed.target_object,
                    objects_by_name=objects_by_name,
                    relation_name=relation_name,
                    role="target_object",
                )
                if (
                    source_object_name == target_object_name
                    and relation_type == RelationTypeEnum.MANY_TO_MANY
                ):
                    raise SeedValidationError(
                        "Self many_to_many relations are not supported in MVP."
                    )

                if relation_type.is_fk_based():
                    relation_spec = self._normalize_fk_relation(
                        relation_seed=relation_seed,
                        relation_name=relation_name,
                        relation_type=relation_type,
                        source_object_name=source_object_name,
                        target_object_name=target_object_name,
                        objects_by_name=objects_by_name,
                        indexes_by_object=indexes_by_object,
                        global_index_names=global_index_names,
                    )
                else:
                    relation_spec = self._normalize_many_to_many_relation(
                        relation_seed=relation_seed,
                        relation_name=relation_name,
                        relation_type=relation_type,
                        source_object_name=source_object_name,
                        target_object_name=target_object_name,
                    )
                relations_by_source_object[source_object_name.plural].append(
                    relation_spec
                )

        objects: list[ValidatedObjectSpec] = []
        for partial in object_partials:
            object_seed = partial.seed
            object_name = partial.name
            object_label = partial.label
            object_kind = partial.kind

            objects.append(
                ValidatedObjectSpec(
                    singular_name=object_name.singular,
                    plural_name=object_name.plural,
                    singular_label=object_label.singular,
                    plural_label=object_label.plural,
                    description=object_seed.description.strip(),
                    kind=object_kind,
                    fields=partial.fields,
                    indexes=tuple(indexes_by_object[object_name.plural]),
                    relations=tuple(relations_by_source_object[object_name.plural]),
                )
            )

        return ValidatedSchemaSpec(
            version=seed.version,
            code=seed.code.strip(),
            label=seed.label.strip(),
            objects=tuple(objects),
        )

    def _normalize_fk_relation(
        self,
        *,
        relation_seed,
        relation_name: str,
        relation_type: RelationTypeEnum,
        source_object_name: ObjectNameVO,
        target_object_name: ObjectNameVO,
        objects_by_name: dict[str, tuple[ObjectNameVO, tuple[ValidatedFieldSpec, ...]]],
        indexes_by_object: dict[str, list[ValidatedIndexSpec]],
        global_index_names: set[str],
    ) -> ValidatedRelationSpec:
        """Валидирует FK-based relation и добавляет generated index metadata."""
        owning_object_name, owning_fields = self._require_object(
            object_name=relation_seed.owning_object,
            objects_by_name=objects_by_name,
            relation_name=relation_name,
            role="owning_object",
        )
        referenced_object_name, referenced_fields = self._require_object(
            object_name=relation_seed.referenced_object,
            objects_by_name=objects_by_name,
            relation_name=relation_name,
            role="referenced_object",
        )
        if relation_type in {
            RelationTypeEnum.MANY_TO_ONE,
            RelationTypeEnum.ONE_TO_ONE,
        }:
            self._ensure_object_matches(
                actual=owning_object_name,
                expected=source_object_name,
                relation_name=relation_name,
                role="owning_object",
            )
            self._ensure_object_matches(
                actual=referenced_object_name,
                expected=target_object_name,
                relation_name=relation_name,
                role="referenced_object",
            )
        if relation_type == RelationTypeEnum.ONE_TO_MANY:
            self._ensure_object_matches(
                actual=owning_object_name,
                expected=target_object_name,
                relation_name=relation_name,
                role="owning_object",
            )
            self._ensure_object_matches(
                actual=referenced_object_name,
                expected=source_object_name,
                relation_name=relation_name,
                role="referenced_object",
            )

        fk_field = self._require_identifier(
            relation_seed.fk_field,
            relation_name=relation_name,
            role="fk_field",
        )
        fk_field_spec = self._require_field(
            field_name=fk_field,
            fields=owning_fields,
            object_name=owning_object_name,
            relation_name=relation_name,
            role="fk_field",
        )
        if fk_field_spec.field_type.code != FieldTypeEnum.REFERENCE:
            raise SeedValidationError(
                f"Relation '{relation_name}' fk_field '{fk_field}' "
                "must have type 'reference'."
            )

        referenced_field = self._require_identifier(
            relation_seed.referenced_field,
            relation_name=relation_name,
            role="referenced_field",
        )
        self._require_field(
            field_name=referenced_field,
            fields=referenced_fields,
            object_name=referenced_object_name,
            relation_name=relation_name,
            role="referenced_field",
        )

        foreign_key_name = SchemaNamingStrategy.foreign_key_name(
            source_table_name=owning_object_name.plural,
            source_column_name=fk_field,
            target_table_name=referenced_object_name.plural,
        )
        fk_index_name = None
        unique_index_name = None
        is_unique = relation_type == RelationTypeEnum.ONE_TO_ONE
        if is_unique:
            unique_index_name = SchemaNamingStrategy.one_to_one_unique_index_name(
                table_name=owning_object_name.plural,
                column_name=fk_field,
            )
            if not self._has_matching_index(
                indexes=indexes_by_object[owning_object_name.plural],
                fields=(fk_field,),
                is_unique=True,
            ):
                self._ensure_global_index_name_is_unique(
                    index_name=unique_index_name,
                    global_index_names=global_index_names,
                )
                indexes_by_object[owning_object_name.plural].append(
                    ValidatedIndexSpec(
                        name=unique_index_name,
                        fields=(fk_field,),
                        is_unique=True,
                        is_generated=True,
                    )
                )
        else:
            fk_index_name = SchemaNamingStrategy.foreign_key_index_name(
                table_name=owning_object_name.plural,
                column_name=fk_field,
            )
            if not self._has_matching_index(
                indexes=indexes_by_object[owning_object_name.plural],
                fields=(fk_field,),
                is_unique=False,
            ):
                self._ensure_global_index_name_is_unique(
                    index_name=fk_index_name,
                    global_index_names=global_index_names,
                )
                indexes_by_object[owning_object_name.plural].append(
                    ValidatedIndexSpec(
                        name=fk_index_name,
                        fields=(fk_field,),
                        is_unique=False,
                        is_generated=True,
                    )
                )

        return ValidatedRelationSpec(
            name=relation_name,
            relation_type=relation_type,
            source_object=source_object_name.singular,
            target_object=target_object_name.singular,
            owning_object=owning_object_name.singular,
            fk_field=fk_field,
            referenced_object=referenced_object_name.singular,
            referenced_field=referenced_field,
            source_relation_name=self._normalize_relation_api_name(
                relation_seed.source_relation_name,
                default=(
                    target_object_name.singular
                    if relation_type != RelationTypeEnum.ONE_TO_MANY
                    else target_object_name.plural
                ),
            ),
            target_relation_name=self._normalize_relation_api_name(
                relation_seed.target_relation_name,
                default=(
                    source_object_name.plural
                    if relation_type != RelationTypeEnum.ONE_TO_MANY
                    else source_object_name.singular
                ),
            ),
            relation_table_name=None,
            source_join_column_name=None,
            target_join_column_name=None,
            on_delete=self._normalize_on_delete(relation_seed.on_delete),
            is_required=relation_seed.is_required,
            is_unique=is_unique,
            kind=self._normalize_relation_kind(relation_seed.kind),
            settings=dict(relation_seed.settings or {}),
            foreign_key_name=foreign_key_name,
            fk_index_name=fk_index_name,
            unique_index_name=unique_index_name,
        )

    def _normalize_many_to_many_relation(
        self,
        *,
        relation_seed,
        relation_name: str,
        relation_type: RelationTypeEnum,
        source_object_name: ObjectNameVO,
        target_object_name: ObjectNameVO,
    ) -> ValidatedRelationSpec:
        """Валидирует many_to_many relation и генерирует имена join-таблицы."""
        relation_table_name = self._validate_identifier(
            relation_seed.relation_table_name
            or f"{source_object_name.plural}_{target_object_name.plural}",
            "Relation table name",
        )
        source_join_column_name = self._validate_identifier(
            relation_seed.source_join_column_name
            or f"{source_object_name.singular}_id",
            "Source join column name",
        )
        target_join_column_name = self._validate_identifier(
            relation_seed.target_join_column_name
            or f"{target_object_name.singular}_id",
            "Target join column name",
        )
        return ValidatedRelationSpec(
            name=relation_name,
            relation_type=relation_type,
            source_object=source_object_name.singular,
            target_object=target_object_name.singular,
            owning_object=None,
            fk_field=None,
            referenced_object=None,
            referenced_field=None,
            source_relation_name=self._normalize_relation_api_name(
                relation_seed.source_relation_name,
                default=target_object_name.plural,
            ),
            target_relation_name=self._normalize_relation_api_name(
                relation_seed.target_relation_name,
                default=source_object_name.plural,
            ),
            relation_table_name=relation_table_name,
            source_join_column_name=source_join_column_name,
            target_join_column_name=target_join_column_name,
            on_delete=self._normalize_on_delete(relation_seed.on_delete),
            is_required=relation_seed.is_required,
            is_unique=False,
            kind=self._normalize_relation_kind(relation_seed.kind),
            settings=dict(relation_seed.settings or {}),
        )

    @staticmethod
    def _require_object(
        *,
        object_name: str | None,
        objects_by_name: dict[str, tuple[ObjectNameVO, tuple[ValidatedFieldSpec, ...]]],
        relation_name: str,
        role: str,
    ) -> tuple[ObjectNameVO, tuple[ValidatedFieldSpec, ...]]:
        """Возвращает object lookup entry или поднимает SeedValidationError."""
        normalized = SchemaSeedService._require_identifier(
            object_name,
            relation_name=relation_name,
            role=role,
        )
        relation_object = objects_by_name.get(normalized)
        if relation_object is None:
            raise SeedValidationError(
                f"Relation '{relation_name}' references unknown {role} "
                f"'{normalized}'."
            )
        return relation_object

    @staticmethod
    def _require_field(
        *,
        field_name: str,
        fields: tuple[ValidatedFieldSpec, ...],
        object_name: ObjectNameVO,
        relation_name: str,
        role: str,
    ) -> ValidatedFieldSpec:
        """Возвращает field spec или поднимает SeedValidationError."""
        for field_spec in fields:
            if field_spec.name == field_name:
                return field_spec
        raise SeedValidationError(
            f"Relation '{relation_name}' references unknown {role} "
            f"'{field_name}' on object '{object_name.plural}'."
        )

    @staticmethod
    def _require_identifier(
        value: str | None,
        *,
        relation_name: str,
        role: str,
    ) -> str:
        """Проверяет обязательное строковое relation поле."""
        normalized = (value or "").strip()
        if not normalized:
            raise SeedValidationError(f"Relation '{relation_name}' requires {role}.")
        return normalized

    @staticmethod
    def _ensure_object_matches(
        *,
        actual: ObjectNameVO,
        expected: ObjectNameVO,
        relation_name: str,
        role: str,
    ) -> None:
        """Проверяет canonical role direction для relation."""
        if actual == expected:
            return
        raise SeedValidationError(
            f"Relation '{relation_name}' has invalid {role} "
            f"'{actual.plural}', expected '{expected.plural}'."
        )

    @staticmethod
    def _has_matching_index(
        *,
        indexes: list[ValidatedIndexSpec],
        fields: tuple[str, ...],
        is_unique: bool,
    ) -> bool:
        """Проверяет наличие индекса с теми же колонками и unique-флагом."""
        return any(
            index.fields == fields and index.is_unique == is_unique for index in indexes
        )

    @staticmethod
    def _normalize_relation_api_name(value: str | None, *, default: str) -> str:
        """Нормализует API-имя relation или возвращает default."""
        return (value or default).strip()

    @staticmethod
    def _validate_identifier(value: str, title: str) -> str:
        """Делегирует валидацию PostgreSQL-идентификатора общей naming-стратегии."""
        return SchemaNamingStrategy.validate_identifier(value, title=title)

    @staticmethod
    def _normalize_relation_type(raw_type: str | RelationTypeEnum) -> RelationTypeEnum:
        """Валидирует тип связи seed."""
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
        return relation_type

    @staticmethod
    def _normalize_on_delete(value: str) -> str:
        """Приводит on_delete из seed к каноническому lowercase-значению."""
        mapping = {
            "restrict": "restrict",
            "cascade": "cascade",
            "set null": "set_null",
            "set_null": "set_null",
            "no action": "no_action",
            "no_action": "no_action",
        }
        normalized = value.strip().lower()
        try:
            return mapping[normalized]
        except KeyError as exc:
            raise SeedValidationError(
                f"Unsupported relation on_delete '{value}'."
            ) from exc

    @staticmethod
    def _normalize_relation_kind(value: str) -> str:
        """Валидирует и нормализует kind relation metadata."""
        normalized = value.strip().lower()
        if normalized not in {"system", "standard", "custom"}:
            raise SeedValidationError(f"Unsupported relation kind '{value}'.")
        return normalized

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
    def _ensure_non_custom_object_does_not_use_custom_prefix(
        *,
        object_name: ObjectNameVO,
        object_kind: ObjectKind,
    ) -> None:
        """Резервирует c_ namespace для custom objects."""
        if object_kind == ObjectKind.CUSTOM:
            return
        if has_custom_object_prefix(object_name.singular) or has_custom_object_prefix(
            object_name.plural
        ):
            raise SeedValidationError(
                "Only custom objects can use the 'c_' name prefix."
            )

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
