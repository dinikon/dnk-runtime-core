from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.content_schema import (
    CatalogItemContentSchemaPort,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.rich_text import RichTextSanitizerPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.catalog_item.command.put_catalog_item_content.command import (
    PutCatalogItemContentCommand,
)
from src.modules.catalog.application.catalog_item.command.put_catalog_item_content.dto import (
    PutCatalogItemContentResultDTO,
)


class PutCatalogItemContentHandler:
    """Координирует put_catalog_item_content; товарные инварианты остаются в CatalogItem."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        clock: ClockPort,
        locales: LocalePort,
        schemas: CatalogItemContentSchemaPort,
        sanitizer: RichTextSanitizerPort,
    ) -> None:
        """Принимает порты конкретного сценария на общей tenant UoW."""
        self._mutations = mutations
        self._clock = clock
        self._locales = locales
        self._schemas = schemas
        self._sanitizer = sanitizer

    async def execute(
        self, command: PutCatalogItemContentCommand
    ) -> PutCatalogItemContentResultDTO:
        """Загружает товар, вызывает доменный метод и сохраняет изменение без commit."""
        item = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_revision
        )
        now = self._clock.now()
        await self._locales.ensure_active(command.locale)
        schema = await self._schemas.get_default()
        values = {
            code: (
                self._sanitizer.clean(value)
                if code in {"desc", "short_desc"}
                else value
            )
            for code, value in command.values.items()
        }
        item.put_content(
            LocaleVO(command.locale),
            values,
            schema,
            command.expected_schema_version,
            command.actor_id,
            now,
        )
        await self._mutations.save(item)
        return PutCatalogItemContentResultDTO(item.id.uuid, item.revision)
