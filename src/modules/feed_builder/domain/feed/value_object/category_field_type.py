from dataclasses import dataclass
from typing import ClassVar, Literal
from uuid import UUID

from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
)
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.field_type_validation import (
    validate_transforms,
)
from src.modules.feed_builder.domain.feed.value_object.category_node import (
    CategoryNodeVO,
)
from src.modules.feed_builder.domain.feed.value_object.category_property import (
    CategoryPropertyVO,
)
from src.modules.feed_builder.domain.feed.value_object.category_rule import (
    CategoryRuleVO,
)
from src.modules.feed_builder.domain.feed.value_object.locale_code import LocaleCodeVO
from src.modules.feed_builder.domain.feed.value_object.transform_definition import (
    TransformDefinitionVO,
)


@dataclass(frozen=True, slots=True)
class CategoryFieldTypeVO:
    """Объединяет схему записи, дерево и правила одного поля."""

    kind: ClassVar[FieldValueType] = FieldValueType.CATEGORY
    properties: tuple[CategoryPropertyVO, ...]
    id_key: str
    label_key: str
    locale: LocaleCodeVO
    nodes: tuple[CategoryNodeVO, ...]
    rules: tuple[CategoryRuleVO, ...]
    fallback: Literal["CATALOG", "FIXED", "NONE"]
    fallback_id: UUID | None
    catalog_priority: tuple[UUID, ...] = ()
    next_export_id: int = 1
    name_transforms: tuple[TransformDefinitionVO, ...] = ()

    def __post_init__(self) -> None:
        """Проверяет схему свойств, значения и ссылки."""
        if (
            not isinstance(self.locale, LocaleCodeVO)
            or self.fallback not in ("CATALOG", "FIXED", "NONE")
            or type(self.next_export_id) is not int
            or not 1 <= self.next_export_id <= 2**53 - 1
            or not isinstance(self.properties, tuple)
            or not 1 <= len(self.properties) <= 64
            or not all(isinstance(item, CategoryPropertyVO) for item in self.properties)
            or not isinstance(self.nodes, tuple)
            or len(self.nodes) > 1000
            or not all(isinstance(node, CategoryNodeVO) for node in self.nodes)
            or not isinstance(self.rules, tuple)
            or len(self.rules) > 100
            or not all(isinstance(rule, CategoryRuleVO) for rule in self.rules)
        ):
            raise InvalidFeedValueError("Некорректное поле категории.")
        object.__setattr__(
            self,
            "name_transforms",
            validate_transforms(
                self.name_transforms,
                allowed=frozenset(
                    (TransformOperation.STRING_TRIM, TransformOperation.STRING_TRUNCATE)
                ),
            ),
        )
        props = {prop.key.value: prop for prop in self.properties}
        output = [
            (prop.placement, prop.name.value if prop.placement != "TEXT" else "")
            for prop in self.properties
            if prop.placement != "NONE"
        ]
        if (
            len(props) != len(self.properties)
            or len(output) != len(set(output))
            or self.id_key not in props
            or props[self.id_key].kind not in ("string", "integer")
            or props[self.id_key].source is not None
            or self.label_key not in props
            or props[self.label_key].kind not in ("string", "text")
        ):
            raise InvalidFeedValueError(
                "Проверьте уникальность свойств, ключ ID и ключ названия категории."
            )
        self._validate_nodes(props)

    def _validate_nodes(self, props: dict[str, CategoryPropertyVO]) -> None:
        """Проверяет значения по схеме и граф связей."""
        nodes = {node.id: node for node in self.nodes}
        catalog = {
            node.catalog_id for node in self.nodes if node.catalog_id is not None
        }
        if (
            len(nodes) != len(self.nodes)
            or len(catalog) != sum(node.catalog_id is not None for node in self.nodes)
            or len({rule.id for rule in self.rules}) != len(self.rules)
            or any(rule.target_id not in nodes for rule in self.rules)
            or self.fallback == "FIXED"
            and self.fallback_id not in nodes
            or self.fallback != "FIXED"
            and self.fallback_id is not None
            or len(set(self.catalog_priority)) != len(self.catalog_priority)
            or any(
                identifier not in nodes or nodes[identifier].catalog_id is None
                for identifier in self.catalog_priority
            )
        ):
            raise InvalidFeedValueError(
                "Правила, приоритет или связи категорий некорректны."
            )
        export_ids: set[str] = set()
        for node in self.nodes:
            values = dict(node.values)
            if any(
                key not in props or not props[key].accepts(value)
                for key, value in values.items()
            ):
                raise InvalidFeedValueError(
                    "Значение записи не соответствует схеме объекта."
                )
            for key, prop in props.items():
                if key not in values and (
                    key == self.id_key
                    or prop.required
                    and not (prop.source and node.catalog_id)
                ):
                    raise InvalidFeedValueError(
                        f"Заполните обязательное свойство «{key}»."
                    )
            identifier = str(values[self.id_key])
            if (
                not identifier.strip()
                or len(identifier) > 128
                or identifier in export_ids
            ):
                raise InvalidFeedValueError(
                    "Экспортные ID должны быть непустыми и уникальными внутри поля."
                )
            export_ids.add(identifier)
        self.ensure_tree({node.id: node.parent_id for node in self.nodes})

    @staticmethod
    def ensure_tree(parents: dict[UUID, UUID | None]) -> None:
        """Отклоняет циклы и отсутствующих родителей."""
        done: set[UUID] = set()
        for identifier in parents:
            branch: set[UUID] = set()
            current: UUID | None = identifier
            while current is not None and current not in done:
                if current not in parents or current in branch:
                    raise InvalidFeedValueError(
                        "В дереве категорий есть цикл или отсутствует родитель."
                    )
                branch.add(current)
                current = parents[current]
            done.update(branch)
