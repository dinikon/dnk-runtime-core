from src.modules.channels.application.publication_import.consumption import (
    PublicationImportConsumptionService,
)
from src.modules.channels.domain.product_representation.policy import (
    ensure_linking_allowed,
)
from dataclasses import asdict
import hashlib
import json
from src.modules.channels.application.product_representation.command.create_catalog_item_from_publication.command import (
    CreateCatalogItemFromPublicationCommand,
)
from src.modules.channels.application.product_representation.command.create_catalog_item_from_publication.dto import (
    CreateCatalogItemFromPublicationResultDTO,
)
from src.modules.channels.application.product_representation.port.catalog_drafts import (
    CatalogDraftCreationFacade,
)
from src.modules.channels.application.product_representation.port.publication_catalog import (
    PublicationCatalogSourcePort,
)
from src.modules.channels.application.product_representation.port.binding_queries import (
    BindingQueriesPort,
)
from src.modules.channels.application.product_representation.port.creation_receipts import (
    CatalogCreationReceiptsPort,
)
from src.modules.channels.application.product_representation.contracts import (
    CatalogCreationReceiptDTO,
)
from src.modules.channels.application.product_representation.linking_service import (
    PublicationLinkingService,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsDraftValidationError,
)


class CreateCatalogItemFromPublicationHandler:
    """Атомарно создаёт наполненный Draft, связь и результат идемпотентного запроса."""

    def __init__(
        self,
        catalog: CatalogDraftCreationFacade,
        sources: PublicationCatalogSourcePort,
        bindings: BindingQueriesPort,
        receipts: CatalogCreationReceiptsPort,
        linking: PublicationLinkingService,
        clock: ClockPort,
        imports: PublicationImportConsumptionService | None = None,
    ) -> None:
        """Получает порты на одном внешнем tenant UoW без commit или сетевых вызовов."""
        self.imports = imports
        (
            self.catalog,
            self.sources,
            self.bindings,
            self.receipts,
            self.linking,
            self.clock,
        ) = (catalog, sources, bindings, receipts, linking, clock)

    async def execute(
        self, command: CreateCatalogItemFromPublicationCommand
    ) -> CreateCatalogItemFromPublicationResultDTO:
        """Проверяет replay раньше observed revision и откатывает всё при любой ошибке."""
        encoded = json.dumps(
            {
                "publication_id": str(command.publication_id),
                "actor_id": str(command.actor_id),
                "observed_revision": command.expected_observed_revision,
                "values": asdict(command.values),
                "preparation_id": (
                    str(command.preparation_id) if command.preparation_id else None
                ),
                "preparation_revision": command.expected_preparation_revision,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        await self.receipts.lock_key(command.tenant_id, command.request_key)
        receipt = await self.receipts.get(command.request_key)
        if receipt:
            if receipt.input_hash != digest:
                raise ChannelsConflictError("idempotency_key_reused")
            return CreateCatalogItemFromPublicationResultDTO(
                receipt.catalog_item_id, receipt.representation_id, receipt.binding_id
            )
        source = await self.sources.source(command.publication_id, lock=True)
        ensure_linking_allowed(source.archived)
        if source.observed_revision != command.expected_observed_revision:
            raise ChannelsConflictError("publication_revision_conflict")
        if await self.bindings.active(command.publication_id):
            raise ChannelsConflictError("publication_already_bound")
        values = command.values
        if command.preparation_id is not None:
            if self.imports is None or command.expected_preparation_revision is None:
                raise ChannelsConflictError("import_preparation_required")
            values = await self.imports.consume(
                source,
                command.actor_id,
                command.preparation_id,
                command.expected_preparation_revision,
                values,
            )
        elif (
            values.descriptions
            or values.gallery
            or values.image_files
            or command.expected_preparation_revision is not None
        ):
            raise ChannelsConflictError("import_preparation_required")
        checked = await self.catalog.validate(
            command.tenant_id, command.actor_id, values
        )
        issues = checked.issues
        if issues:
            raise ChannelsDraftValidationError(issues)
        item_id = await self.catalog.create(command.tenant_id, command.actor_id, values)
        binding = await self.linking.attach(source, item_id, None, command.actor_id)
        await self.receipts.add(
            CatalogCreationReceiptDTO(
                command.request_key,
                command.publication_id,
                digest,
                source.observed_revision,
                item_id,
                binding.representation_id,
                binding.binding_id,
            ),
            command.actor_id,
            self.clock.now(),
        )
        return CreateCatalogItemFromPublicationResultDTO(
            item_id, binding.representation_id, binding.binding_id
        )
