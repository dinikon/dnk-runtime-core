from dataclasses import dataclass, replace
from uuid import UUID

from src.modules.feed_builder.application.feed.port.catalog_category_tree import (
    SourceCategoryDTO,
)
from src.modules.feed_builder.application.feed.service.xml_document import (
    XmlDocumentSection,
    XmlElement,
)
from src.modules.feed_builder.domain.feed.calculation.evaluator import calculate_boolean
from src.modules.feed_builder.domain.feed.entity.field_definition import FieldDefinition
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.field_type_validation import (
    apply_text_transforms,
)
from src.modules.feed_builder.domain.feed.value_object.calculation_inputs import (
    CalculationInputsVO,
)
from src.modules.feed_builder.domain.feed.value_object.category_field_type import (
    CategoryFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.category_property import (
    CategoryScalar,
)
from src.modules.feed_builder.domain.publication.service.field_value_resolver import (
    FieldIssue,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CategoryAssignment:
    """Связывает выбранную запись с полем и объясняет выбор в предпросмотре."""

    field_id: UUID
    field_label: str
    node_id: UUID
    export_id: str
    path: tuple[str, ...]
    rule_label: str | None
    reference: CategoryScalar | None


def _xml_scalar(value: CategoryScalar) -> str:
    """Представляет примитив в XML с сохранением false и нуля."""
    return str(value).lower() if type(value) is bool else str(value)


class CategoryExportResolver:
    """Подготавливает одно поле независимо от остальных полей фида."""

    def __init__(
        self, field: FieldDefinition, sources: tuple[SourceCategoryDTO, ...]
    ) -> None:
        """Фиксирует дерево и свойства на одном снимке Catalog."""
        definition = field.type_definition
        assert isinstance(definition, CategoryFieldTypeVO)
        self.definition = definition
        self.field = field
        self._by_catalog = {
            node.catalog_id: node.id
            for node in definition.nodes
            if node.catalog_id is not None
        }
        source_by_id = {node.id: node for node in sources}
        self._source_parents = {node.id: node.parent_id for node in sources}
        self._values: dict[UUID, dict[str, CategoryScalar]] = {}
        self._parents: dict[UUID, UUID | None] = {}
        for node in definition.nodes:
            source = source_by_id.get(node.catalog_id) if node.catalog_id else None
            if node.catalog_id is not None and source is None:
                raise InvalidFeedValueError(
                    f"В поле «{field.label.value}» категория Catalog недоступна."
                )
            parent = node.parent_id
            if (
                node.inherit_parent
                and source is not None
                and source.parent_id is not None
            ):
                parent = self._by_catalog.get(source.parent_id)
                if parent is None:
                    raise InvalidFeedValueError(
                        f"Подключите родителя из Catalog в поле «{field.label.value}»."
                    )
            values = dict(node.values)
            for prop in definition.properties:
                key = prop.key.value
                if (
                    key not in values
                    and source is not None
                    and prop.source == "CATALOG_NAME"
                ):
                    values[key] = source.name
                if key == definition.label_key and isinstance(
                    name := values.get(key), str
                ):
                    values[key] = apply_text_transforms(
                        name, definition.name_transforms
                    )
                if key in values and not prop.accepts(values[key]):
                    raise InvalidFeedValueError(
                        f"Недопустимое значение «{key}» в поле «{field.label.value}»."
                    )
            self._values[node.id] = values
            self._parents[node.id] = parent
        CategoryFieldTypeVO.ensure_tree(self._parents)

    def resolve(
        self, inputs: CalculationInputsVO
    ) -> CategoryAssignment | FieldIssue | None:
        """Выбирает запись первого совпавшего правила или явного варианта ELSE."""
        expanded = None
        for rule in self.definition.rules:
            selected = inputs
            if rule.include_descendants:
                if expanded is None:
                    expanded = self._with_ancestors(inputs)
                selected = expanded
            result = calculate_boolean(rule.calculation, selected)
            if result.issues:
                issue = result.issues[0]
                return FieldIssue(
                    self.field.id.uuid,
                    issue.code,
                    issue.message,
                    ("value", *issue.path),
                    rule.id,
                )
            if result.value is True:
                return self._assignment(rule.target_id, rule.label)
        if self.definition.fallback == "FIXED":
            assert self.definition.fallback_id is not None
            return self._assignment(self.definition.fallback_id, None)
        if self.definition.fallback == "CATALOG":
            matches = {
                self._by_catalog[item.uuid]
                for item in inputs.category_ids
                if item.uuid in self._by_catalog
            }
            if len(matches) == 1:
                return self._assignment(next(iter(matches)), None)
            if matches:
                for identifier in self.definition.catalog_priority:
                    if identifier in matches:
                        return self._assignment(identifier, None)
                return FieldIssue(
                    self.field.id.uuid,
                    "CATEGORY_AMBIGUOUS",
                    "Найдено несколько категорий. Задайте приоритет.",
                    ("value",),
                )
        if self.field.export.required:
            return self._missing_reference()
        return None

    def document(self, used: set[UUID]) -> XmlDocumentSection | None:
        """Готовит коллекцию из выбранных записей и родителей либо из всего дерева."""
        layout = self.field.export.document
        if layout is None:
            return None
        if self.field.export.publication_key is None:
            used = set(self._values)
        order: list[UUID] = []
        seen: set[UUID] = set()
        for identifier in self._values:
            if identifier not in used:
                continue
            branch = []
            current: UUID | None = identifier
            while current is not None and current not in seen:
                branch.append(current)
                seen.add(current)
                current = self._parents[current]
            order.extend(reversed(branch))
        if layout.layout == "FLAT":
            return XmlDocumentSection(
                layout.parent,
                XmlElement(
                    layout.container.value,
                    children=tuple(self._element(identifier) for identifier in order),
                ),
            )
        children: dict[UUID | None, list[XmlElement]] = {}
        for identifier in reversed(order):
            nested = tuple(reversed(children.get(identifier, [])))
            children.setdefault(self._parents[identifier], []).append(
                self._element(identifier, nested)
            )
        return XmlDocumentSection(
            layout.parent,
            XmlElement(
                layout.container.value,
                children=tuple(reversed(children.get(None, []))),
            ),
        )

    def _element(
        self, identifier: UUID, nested: tuple[XmlElement, ...] = ()
    ) -> XmlElement:
        """Отображает только значения, явно направленные в XML."""
        layout = self.field.export.document
        assert layout is not None
        values = self._values[identifier]
        attributes: list[tuple[str, str]] = []
        children: list[XmlElement] = []
        text = None
        for prop in self.definition.properties:
            value = values.get(prop.key.value)
            if value is None:
                continue
            content = _xml_scalar(value)
            if prop.placement == "ATTRIBUTE":
                attributes.append((prop.name.value, content))
            elif prop.placement == "ELEMENT":
                children.append(XmlElement(prop.name.value, text=content))
            elif prop.placement == "TEXT":
                text = content
        parent = self._parents[identifier]
        if layout.layout == "FLAT" and parent is not None:
            attributes.append(
                (
                    layout.parent_attribute.value,
                    _xml_scalar(self._values[parent][self.definition.id_key]),
                )
            )
        return XmlElement(
            layout.item.value, tuple(attributes), text, (*children, *nested)
        )

    def _with_ancestors(self, inputs: CalculationInputsVO) -> CalculationInputsVO:
        """Расширяет членство Catalog только для условий с потомками."""
        included: set[UUID] = set()
        for category in inputs.category_ids:
            current: UUID | None = category.uuid
            while current is not None and current not in included:
                included.add(current)
                current = self._source_parents.get(current)
        return replace(
            inputs, category_ids=tuple(EntityIdVO(item) for item in sorted(included))
        )

    def _assignment(
        self, identifier: UUID, rule_label: str | None
    ) -> CategoryAssignment | FieldIssue:
        """Передаёт значение выбранного свойства и путь записи."""
        values = self._values[identifier]
        export = self.field.export
        reference = (
            values.get(export.publication_key.value)
            if export.publication_key is not None
            else None
        )
        if export.required and (
            reference is None or isinstance(reference, str) and not reference.strip()
        ):
            return self._missing_reference()
        names: list[str] = []
        current: UUID | None = identifier
        while current is not None:
            entry = self._values[current]
            names.append(
                str(
                    entry.get(self.definition.label_key)
                    or entry[self.definition.id_key]
                )
            )
            current = self._parents[current]
        return CategoryAssignment(
            self.field.id.uuid,
            self.field.label.value,
            identifier,
            _xml_scalar(values[self.definition.id_key]),
            tuple(reversed(names)),
            rule_label,
            reference,
        )

    def _missing_reference(self) -> FieldIssue:
        """Привязывает диагностику отсутствующей ссылки к полю."""
        return FieldIssue(
            self.field.id.uuid,
            "CATEGORY_REQUIRED",
            "Для предложения требуется значение ссылки на категорию.",
            ("value",),
        )
