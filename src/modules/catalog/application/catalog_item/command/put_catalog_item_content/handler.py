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
from src.modules.catalog.domain.catalog_item.value_object.override import (
    OverrideMode,
    OverrideVO,
)
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
        """Загружает семью, вызывает доменный метод и сохраняет изменение без commit."""
        root = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_root_revision
        )
        now = self._clock.now()
        await self._locales.ensure_active(command.locale)
        schema = await self._schemas.get_default()
        values = {
            k: OverrideVO(
                v.mode,
                (
                    self._sanitizer.clean(v.value)
                    if k in {"desc", "short_desc"} and v.mode == OverrideMode.SET
                    else v.value
                ),
            )
            for k, v in command.values.items()
        }
        root.put_content(
            command.item_id,
            LocaleVO(command.locale),
            values,
            schema,
            command.expected_schema_version,
            command.actor_id,
            now,
        )
        await self._mutations.save(root)
        item = root.find_item(command.item_id)
        return PutCatalogItemContentResultDTO(
            item.id.uuid, root.id.uuid, item.revision, root.revision
        )
