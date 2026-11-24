from src.modules.feed_builder.domain.feed.value_object.category_field_type import (
    CategoryFieldTypeVO,
)
from src.modules.feed_builder.application.feed.port.catalog_category_tree import (
    SourceCategoryDTO,
)
from dataclasses import dataclass, replace
from datetime import datetime
import re
from uuid import UUID

from src.modules.feed_builder.domain.feed.types import ResolvedFieldValue
from src.modules.feed_builder.domain.feed.validation import is_xml_text
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.application.feed.port.catalog_category_tree import (
    CatalogCategoryTreePort,
)
from src.modules.feed_builder.application.feed.service.category_export import (
    CategoryAssignment,
    CategoryExportResolver,
)
from src.modules.feed_builder.domain.feed.value_object.string_field_type import (
    StringFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_field_type import (
    TextFieldTypeVO,
)
from src.modules.feed_builder.application.feed.export_settings_dto import (
    CsvExportSettingsDTO,
    XmlExportSettingsDTO,
)
from src.modules.feed_builder.application.feed.port.query_repository import (
    FeedQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.feed.query.get_feed.dto import FeedDetailsDTO
from src.modules.feed_builder.application.feed.schema_definition import decode_schema
from src.modules.feed_builder.application.feed.export_settings import settings_to_dto
from src.modules.feed_builder.application.feed.schema_document import schema_document
from src.modules.feed_builder.domain.export_state.value_object.export_snapshot import (
    ExportSnapshotVO,
)
from src.modules.feed_builder.application.publication.port.export_source import (
    PublicationCatalogAccessPort,
    PublicationCatalogValuesPort,
    PublicationExportReaderProtocol,
    PublicationCursor,
    PublicationExportSource,
    CatalogReference,
)
from src.modules.feed_builder.domain.feed.entity.field_definition import FieldDefinition
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.error import (
    FeedArchivedError,
    FeedNotFoundError,
    FeedVersionConflictError,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.price_value import PriceValueVO
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.publication.service.field_value_resolver import (
    FieldIssue,
)
from src.modules.feed_builder.domain.publication.service.publication_resolver import (
    PublicationResolver,
)
from src.modules.feed_builder.domain.publication.value_object.publication_catalog_snapshot import (
    PublicationCatalogSnapshotVO,
)
from src.modules.shared.domain.time.clock_port import ClockPort


@dataclass(frozen=True, slots=True)
class PublicationExportContext:
    """Фиксирует схему, настройки, порядок колонок и время расчёта одного запроса."""

    feed: FeedDetailsDTO
    schema: FeedSchemaVO
    exported_fields: tuple[FieldDefinition, ...]
    as_of: datetime
    locales: frozenset[str]
    sources: frozenset[str]
    category_fields: tuple[CategoryExportResolver, ...] = ()


@dataclass(frozen=True, slots=True)
class ExportRecord:
    """Содержит итоговые значения колонок и диагностику одной публикации."""

    publication_id: UUID
    catalog_item_id: UUID
    catalog_variant_id: UUID | None
    sku: str | None
    values: tuple[ResolvedFieldValue, ...]
    issues: tuple[FieldIssue, ...]
    readiness: str
    warnings: tuple[FieldIssue, ...] = ()
    categories: tuple[CategoryAssignment, ...] = ()


class PublicationExportService:
    """Собирает контекст и пакет записей для предпросмотра и тестового файла."""

    def __init__(
        self,
        feeds: FeedQueryRepositoryProtocol,
        publications: PublicationExportReaderProtocol,
        products: PublicationCatalogValuesPort,
        access: PublicationCatalogAccessPort,
        clock: ClockPort,
        categories: CatalogCategoryTreePort | None = None,
    ) -> None:
        """Принимает только порты чтения и доверенный контекст доступа."""
        self._feeds = feeds
        self._publications = publications
        self._products = products
        self._access = access
        self._clock = clock
        self._categories = categories

    async def prepare(
        self, feed_id: FeedIdVO, expected_version: int
    ) -> PublicationExportContext:
        """Читает одно сохранённое определение и собирает потребности его полей."""
        return await self._prepare(feed_id, expected_version)

    async def prepare_for_editor(self, feed_id: FeedIdVO) -> PublicationExportContext:
        """Читает актуальную схему в том числе для карточки архивной публикации."""
        return await self._prepare(feed_id, None, include_categories=False)

    async def _prepare(
        self,
        feed_id: FeedIdVO,
        expected_version: int | None,
        *,
        include_categories: bool = True,
    ) -> PublicationExportContext:
        """Фиксирует одну сохранённую схему и потребности её полей."""
        feed = await self._feeds.get_details(feed_id)
        if feed is None:
            raise FeedNotFoundError("Feed не найден.")
        if expected_version is not None and feed.version != expected_version:
            raise FeedVersionConflictError("Feed уже изменён.")
        if expected_version is not None and feed.status == "ARCHIVED":
            raise FeedArchivedError("Архивный Feed доступен только для просмотра.")
        return await self._context(
            feed,
            decode_schema(feed.schema),
            self._clock.now(),
            include_categories=include_categories,
        )

    async def prepare_for_refresh(
        self, feed_id: FeedIdVO, snapshot: ExportSnapshotVO, as_of: datetime
    ) -> PublicationExportContext:
        """Использует сохранённые параметры задачи независимо от новых правок Feed."""
        feed = await self._feeds.get_details(feed_id)
        if feed is None:
            raise FeedNotFoundError("Feed не найден.")
        captured = replace(
            feed,
            schema=schema_document(snapshot.schema),
            export_settings=settings_to_dto(snapshot.settings),
        )
        return await self._context(captured, snapshot.schema, as_of)

    async def _context(
        self,
        feed: FeedDetailsDTO,
        schema: FeedSchemaVO,
        as_of: datetime,
        *,
        include_categories: bool = True,
    ) -> PublicationExportContext:
        """Собирает зависимости схемы и общий контекст чтения."""
        locales: set[str] = set()
        sources: set[str] = set()
        for field in schema.fields:
            settings = field.type_definition
            if not isinstance(
                settings, (StringFieldTypeVO, TextFieldTypeVO)
            ) or not isinstance(settings.value_definition, SourceValueDefinitionVO):
                continue
            path = settings.value_definition.source.path
            if path in (CatalogSourcePath.TITLE, CatalogSourcePath.DESCRIPTION):
                sources.add(path.value)
                if settings.locale is not None:
                    locales.add(settings.locale.value)
                if settings.fallback_policy is not None:
                    locales.update(
                        locale.value for locale in settings.fallback_policy.locales
                    )
        category_fields = []
        catalog_trees: dict[str, tuple[SourceCategoryDTO, ...]] = {}
        if include_categories and isinstance(
            feed.export_settings.format_settings, XmlExportSettingsDTO
        ):
            for field in schema.fields:
                definition = field.type_definition
                if not field.export.enabled or not isinstance(
                    definition, CategoryFieldTypeVO
                ):
                    continue
                source = ()
                if any(node.catalog_id is not None for node in definition.nodes) or any(
                    rule.include_descendants for rule in definition.rules
                ):
                    if self._categories is None:
                        raise InvalidFeedValueError("Дерево Catalog недоступно.")
                    locale = definition.locale.value
                    if locale not in catalog_trees:
                        catalog_trees[locale] = await self._categories.read(locale)
                    source = catalog_trees[locale]
                category_fields.append(CategoryExportResolver(field, source))
        references = {
            resolver.field.id
            for resolver in category_fields
            if resolver.field.export.publication_key is not None
        }
        exported = tuple(
            field
            for field in schema.fields
            if field.export.enabled
            and (
                not isinstance(field.type_definition, CategoryFieldTypeVO)
                or field.id in references
            )
        )
        return PublicationExportContext(
            feed,
            schema,
            exported,
            as_of,
            frozenset(locales),
            frozenset(sources),
            tuple(category_fields),
        )

    async def count_enabled(self, feed_id: FeedIdVO) -> int:
        """Возвращает размер включённого ассортимента."""
        return await self._publications.count_enabled(feed_id)

    async def read_enabled(
        self,
        feed_id: FeedIdVO,
        limit: int,
        before: PublicationCursor | None = None,
    ) -> tuple[PublicationExportSource, ...]:
        """Читает пакет включённых публикаций фида."""
        return await self._publications.read_enabled(feed_id, limit, before)

    async def resolve(
        self,
        context: PublicationExportContext,
        items: tuple[PublicationExportSource, ...],
    ) -> tuple[ExportRecord, ...]:
        """Проверяет доступ, читает Catalog один раз для пакета и готовит колонки."""
        if not items:
            return ()
        snapshots = await self.read_catalog(context, items)
        resolver = PublicationResolver()
        locales = {
            field.id.uuid: field.type_definition.locale.value
            for field in context.schema.fields
            if isinstance(field.type_definition, (StringFieldTypeVO, TextFieldTypeVO))
            and field.type_definition.locale
        }
        records: list[ExportRecord] = []
        for item in items:
            snapshot = snapshots.get(item.reference)
            publication = resolver.resolve(
                item.id, context.schema, item.overrides, snapshot
            )
            fields = {field.field_id: field.value for field in publication.fields}
            assignments: list[CategoryAssignment] = []
            category_issues: list[FieldIssue] = []
            if snapshot is not None:
                for category in context.category_fields:
                    if category.field.export.publication_key is None:
                        continue
                    result = category.resolve(snapshot.inputs)
                    if isinstance(result, FieldIssue):
                        category_issues.append(result)
                    elif result is not None:
                        assignments.append(result)
                        fields[result.field_id] = result.reference
            format_issues = (*self.format_issues(context, fields), *category_issues)
            records.append(
                ExportRecord(
                    publication_id=item.id,
                    catalog_item_id=item.reference[0],
                    catalog_variant_id=item.reference[1],
                    sku=snapshot.inputs.sku if snapshot is not None else None,
                    values=tuple(
                        fields.get(field.id.uuid) for field in context.exported_fields
                    ),
                    issues=(*publication.issues, *format_issues),
                    readiness="INVALID" if format_issues else publication.readiness,
                    categories=tuple(assignments),
                    warnings=tuple(
                        FieldIssue(
                            field.field_id,
                            "LOCALE_FALLBACK",
                            "Использован текст из резервной локали.",
                        )
                        for field in publication.fields
                        if field.actual_locale is not None
                        and field.actual_locale != locales.get(field.field_id)
                    ),
                )
            )
        return tuple(records)

    async def read_catalog(
        self,
        context: PublicationExportContext,
        items: tuple[PublicationExportSource, ...],
    ) -> dict[CatalogReference, PublicationCatalogSnapshotVO]:
        """Читает подготовленные значения Catalog после проверки доступа."""
        ids = tuple(
            sorted(
                {
                    identifier
                    for item in items
                    for identifier in item.reference
                    if identifier is not None
                }
            )
        )
        await self._access.ensure_readable(ids)
        return await self._products.read(
            tuple(item.reference for item in items),
            context.as_of,
            context.locales,
            context.sources,
        )

    @staticmethod
    def format_issues(
        context: PublicationExportContext, fields: dict[UUID, ResolvedFieldValue]
    ) -> tuple[FieldIssue, ...]:
        """Возвращает блокирующие ошибки выбранного формата по экспортируемым полям."""
        settings = context.feed.export_settings.format_settings
        if isinstance(settings, XmlExportSettingsDTO):
            return tuple(
                FieldIssue(
                    field.id.uuid,
                    "XML_INVALID_CHARACTER",
                    "Текст содержит символ, недопустимый в XML 1.0.",
                )
                for field in context.exported_fields
                if isinstance(value := fields.get(field.id.uuid), str)
                and not is_xml_text(value)
            )
        return tuple(
            FieldIssue(
                field.id.uuid,
                "CSV_FORMULA_LIKE_TEXT",
                "Текст начинается как формула электронной таблицы. Исправьте значение для CSV.",
            )
            for field in context.exported_fields
            if isinstance(settings, CsvExportSettingsDTO)
            and _csv_formula_like(fields.get(field.id.uuid))
        )


def csv_cell(value: ResolvedFieldValue) -> str | None:
    """Представляет типизированное значение точно как в табличном экспорте."""
    if isinstance(value, PriceValueVO):
        amount = format(value.amount.amount, "f")
        return (
            f"{amount} {value.currency.value}" if value.currency is not None else amount
        )
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    return value


def xml_attribute_cell(value: ResolvedFieldValue) -> str | None:
    """Возвращает значение XML-атрибута до экранирования в сериализаторе."""
    if isinstance(value, PriceValueVO):
        return format(value.amount.amount, "f")
    return csv_cell(value)


def _csv_formula_like(value: ResolvedFieldValue) -> bool:
    """Отклоняет формулоподобный текст, сохраняя числа и исходные значения."""
    if not isinstance(value, str):
        return False
    stripped = value.lstrip()
    return (
        stripped.startswith(("=", "+", "-", "@", "＝", "＋", "－", "＠"))
        and re.fullmatch(
            r"[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", stripped.strip()
        )
        is None
    )
