from dataclasses import dataclass
from datetime import datetime
import re
from uuid import UUID

from src.modules.feed_builder.application.feed.export_settings_dto import (
    CsvExportSettingsDTO,
)
from src.modules.feed_builder.application.feed.port.query_repository import (
    FeedQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.feed.query.get_feed.dto import FeedDetailsDTO
from src.modules.feed_builder.application.feed.schema_definition import decode_schema
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
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
)
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


@dataclass(frozen=True, slots=True)
class ExportRecord:
    """Содержит итоговые значения колонок и диагностику одной публикации."""

    publication_id: UUID
    catalog_item_id: UUID
    catalog_variant_id: UUID | None
    sku: str | None
    values: tuple[str | PriceValueVO | None, ...]
    issues: tuple[FieldIssue, ...]
    readiness: str


class PublicationExportService:
    """Собирает контекст и пакет записей для предпросмотра и тестового файла."""

    def __init__(
        self,
        feeds: FeedQueryRepositoryProtocol,
        publications: PublicationExportReaderProtocol,
        products: PublicationCatalogValuesPort,
        access: PublicationCatalogAccessPort,
        clock: ClockPort,
    ) -> None:
        """Принимает только порты чтения и доверенный контекст доступа."""
        self._feeds = feeds
        self._publications = publications
        self._products = products
        self._access = access
        self._clock = clock

    async def prepare(
        self, feed_id: FeedIdVO, expected_version: int
    ) -> PublicationExportContext:
        """Читает одно сохранённое определение и собирает потребности его полей."""
        return await self._prepare(feed_id, expected_version)

    async def prepare_for_editor(self, feed_id: FeedIdVO) -> PublicationExportContext:
        """Читает актуальную схему в том числе для карточки архивной публикации."""
        return await self._prepare(feed_id, None)

    async def _prepare(
        self, feed_id: FeedIdVO, expected_version: int | None
    ) -> PublicationExportContext:
        """Фиксирует одну сохранённую схему и потребности её полей."""
        feed = await self._feeds.get_details(feed_id)
        if feed is None:
            raise FeedNotFoundError("Feed не найден.")
        if expected_version is not None and feed.version != expected_version:
            raise FeedVersionConflictError("Feed уже изменён.")
        if expected_version is not None and feed.status == "ARCHIVED":
            raise FeedArchivedError("Архивный Feed доступен только для просмотра.")
        schema = decode_schema(feed.schema)
        locales: set[str] = set()
        sources: set[str] = set()
        for field in schema.fields:
            settings = field.type_definition
            if isinstance(settings, MoneyFieldTypeVO) or not isinstance(
                settings.value_definition, SourceValueDefinitionVO
            ):
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
        return PublicationExportContext(
            feed,
            schema,
            tuple(field for field in schema.fields if field.export.enabled),
            self._clock.now(),
            frozenset(locales),
            frozenset(sources),
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
        records: list[ExportRecord] = []
        for item in items:
            snapshot = snapshots.get(item.reference)
            publication = resolver.resolve(
                item.id, context.schema, item.overrides, snapshot
            )
            fields = {field.field_id: field.value for field in publication.fields}
            csv_issues = self.csv_issues(context, fields)
            records.append(
                ExportRecord(
                    publication_id=item.id,
                    catalog_item_id=item.reference[0],
                    catalog_variant_id=item.reference[1],
                    sku=snapshot.inputs.sku if snapshot is not None else None,
                    values=tuple(
                        fields.get(field.id.uuid) for field in context.exported_fields
                    ),
                    issues=(*publication.issues, *csv_issues),
                    readiness="INVALID" if csv_issues else publication.readiness,
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
    def csv_issues(
        context: PublicationExportContext, fields: dict[UUID, str | PriceValueVO | None]
    ) -> tuple[FieldIssue, ...]:
        """Возвращает диагностику CSV для полей в сохранённом порядке экспорта."""
        if not isinstance(
            context.feed.export_settings.format_settings, CsvExportSettingsDTO
        ):
            return ()
        return tuple(
            FieldIssue(
                field.id.uuid,
                "CSV_FORMULA_LIKE_TEXT",
                "Текст начинается как формула электронной таблицы. Исправьте значение для CSV.",
            )
            for field in context.exported_fields
            if _csv_formula_like(fields.get(field.id.uuid))
        )


def csv_cell(value: str | PriceValueVO | None) -> str | None:
    """Представляет типизированное значение точно как в табличном экспорте."""
    if isinstance(value, PriceValueVO):
        amount = format(value.amount.amount, "f")
        return (
            f"{amount} {value.currency.value}" if value.currency is not None else amount
        )
    return value


def _csv_formula_like(value: str | PriceValueVO | None) -> bool:
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
