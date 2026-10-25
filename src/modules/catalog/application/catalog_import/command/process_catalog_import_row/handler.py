from dataclasses import replace
from src.modules.catalog.application.catalog_import.command.process_catalog_import_row.command import (
    ProcessCatalogImportRowCommand,
)
from src.modules.catalog.application.catalog_import.command.process_catalog_import_row.dto import (
    ProcessCatalogImportRowResultDTO,
)
from src.modules.catalog.application.catalog_import.contracts import (
    ImportRowsPort,
    ImportRowResult,
)
from src.modules.catalog.application.catalog_import.values import (
    mapped_values,
    product_values,
    scalar,
)
from src.modules.catalog.domain.catalog_import.repository import CatalogImportRepository
from src.modules.catalog.application.catalog_item.creation_service import (
    CatalogItemCreationService,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.update_service import (
    CatalogItemUpdateService,
)
from src.modules.catalog.application.catalog_item.command.update_catalog_item.command import (
    UpdateCatalogItemCommand,
    UpdateCatalogItemContent,
)
from src.modules.catalog.application.catalog_item.port.content_schema import (
    CatalogItemContentSchemaPort,
)
from src.modules.catalog.domain.catalog_item.repository import (
    CatalogItemRepositoryProtocol,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.error import (
    InvalidCatalogValueError,
    CatalogConflictError,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort


class ProcessCatalogImportRowHandler:
    """Применяет одну позицию в общей транзакции товара и журнала."""

    def __init__(
        self,
        tenant_id: EntityIdVO,
        imports: CatalogImportRepository,
        rows: ImportRowsPort,
        items: CatalogItemRepositoryProtocol,
        creation: CatalogItemCreationService,
        mutations: CatalogItemMutationService,
        updates: CatalogItemUpdateService,
        schemas: CatalogItemContentSchemaPort,
        clock: ClockPort,
    ) -> None:
        """Получает только порты и сервисы текущего внешнего UoW."""
        self.tenant_id, self.imports, self.rows = tenant_id, imports, rows
        self.items, self.creation, self.mutations = items, creation, mutations
        self.updates, self.schemas, self.clock = updates, schemas, clock

    async def execute(
        self, command: ProcessCatalogImportRowCommand
    ) -> ProcessCatalogImportRowResultDTO:
        """Создаёт или обновляет товар, затем учитывает результат в том же UoW."""
        entity = await self.imports.get(EntityIdVO(command.import_id), lock=True)
        next_row = await self.rows.next_row(command.import_id)
        if next_row is None or next_row.number != command.row.number:
            return ProcessCatalogImportRowResultDTO(
                ImportRowResult(command.row.number, "skipped"), False
            )
        entity.begin(self.clock.now())
        values = mapped_values(entity.configuration, command.row.values)
        sku = scalar(values, "sku") or None
        mode = entity.configuration.mode
        if mode != "create" and not sku:
            raise InvalidCatalogValueError(
                "Для обновления и смешанного режима требуется SKU.", ("sku",)
            )
        if sku and await self.rows.duplicate(entity.id.uuid, command.row.number, sku):
            result = ImportRowResult(
                command.row.number,
                "skipped",
                sku,
                warnings=("Повтор SKU внутри источника: используется первая запись.",),
            )
        else:
            identifier = await self.rows.find_item(sku) if sku else None
            if (identifier and mode == "create") or (
                identifier is None and mode == "update"
            ):
                result = ImportRowResult(
                    command.row.number,
                    "skipped",
                    sku,
                    identifier,
                    warnings=(
                        "SKU уже существует." if identifier else "SKU не найден.",
                    ),
                )
            elif identifier is None:
                prepared = product_values(entity.configuration, values)
                product = replace(prepared.product, galleries=command.galleries)
                item = await self.creation.prepare(
                    self.tenant_id, entity.actor_id, product
                )
                await self.items.add(item)
                result = ImportRowResult(
                    command.row.number,
                    "created",
                    sku,
                    item.id.uuid,
                    warnings=command.warnings,
                )
            else:
                item = await self.mutations.load(
                    self.tenant_id, CatalogItemIdVO(identifier)
                )
                if item.sku is None or item.sku.value != sku:
                    raise CatalogConflictError(
                        "SKU товара изменился во время импорта. Проверьте строку и повторите импорт.",
                        ("sku",),
                    )
                prepared = product_values(entity.configuration, values, item)
                # Ошибка хотя бы одного фото сохраняет старую галерею целиком.
                galleries = (
                    command.galleries
                    if not any(w.startswith("Фото:") for w in command.warnings)
                    else {}
                )
                product = prepared.product
                fields = prepared.fields - {"sku"}
                if fields:
                    await self.updates.apply(
                        UpdateCatalogItemCommand(
                            self.tenant_id,
                            entity.actor_id,
                            item.id,
                            fields,
                            status=product.status,
                            virtual=product.virtual,
                            price_specification=product.price_specification,
                            stock=product.stock,
                            weight=product.weight,
                            dimensions=product.dimensions,
                        )
                    )
                schema = await self.schemas.get_by_id(item.product_type_id)
                for locale in sorted(prepared.content_locales | galleries.keys()):
                    localized = frozenset(
                        ({"content"} if locale in prepared.content_locales else set())
                        | ({"gallery"} if locale in galleries else set())
                    )
                    await self.updates.apply(
                        UpdateCatalogItemCommand(
                            self.tenant_id,
                            entity.actor_id,
                            item.id,
                            localized,
                            locale=locale,
                            content=(
                                UpdateCatalogItemContent(
                                    schema.schema_version,
                                    product.translations[locale].values,
                                )
                                if locale in prepared.content_locales
                                else None
                            ),
                            gallery=galleries.get(locale),
                        )
                    )
                result = ImportRowResult(
                    command.row.number,
                    "updated",
                    sku,
                    identifier,
                    warnings=command.warnings,
                )
        await self.rows.finish(entity.id.uuid, result)
        entity.record(result.outcome, len(result.warnings), self.clock.now())
        await self.imports.save(entity)
        return ProcessCatalogImportRowResultDTO(result)
