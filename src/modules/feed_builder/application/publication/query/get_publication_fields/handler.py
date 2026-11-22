from src.modules.feed_builder.application.feed.service.publication_export import (
    PublicationExportService,
    csv_cell,
)
from src.modules.feed_builder.application.publication.port.export_source import (
    PublicationExportReaderProtocol,
)
from src.modules.feed_builder.application.publication.query.get_publication_fields.dto import (
    GetPublicationFieldsResultDTO,
    PublicationFieldDTO,
)
from src.modules.feed_builder.application.publication.query.get_publication_fields.query import (
    GetPublicationFieldsQuery,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
from src.modules.feed_builder.domain.publication.error import PublicationNotFoundError
from src.modules.feed_builder.domain.publication.service.publication_resolver import (
    PublicationResolver,
)


class GetPublicationFieldsHandler:
    """Читает схему и готовит исходные и итоговые значения одной публикации."""

    def __init__(
        self,
        publications: PublicationExportReaderProtocol,
        export: PublicationExportService,
    ) -> None:
        """Получает порты чтения и общий расчёт публикации."""
        self._publications, self._export = publications, export

    async def execute(
        self, query: GetPublicationFieldsQuery
    ) -> GetPublicationFieldsResultDTO:
        """Считает оба режима на одном снимке Catalog и в одно время."""
        feed_id = FeedIdVO(query.feed_id)
        context = await self._export.prepare_for_editor(feed_id)
        source = await self._publications.read_for_editor(feed_id, query.publication_id)
        if source is None:
            raise PublicationNotFoundError("Публикация не найдена.")
        item = source.publication
        snapshot = None
        if context.schema.fields:
            snapshot = (await self._export.read_catalog(context, (item,))).get(
                item.reference
            )
        resolver = PublicationResolver()
        original = resolver.resolve(item.id, context.schema, (), snapshot)
        current = (
            resolver.resolve(item.id, context.schema, item.overrides, snapshot)
            if item.overrides
            else original
        )
        originals = {field.field_id: field for field in original.fields}
        resolved = {field.field_id: field for field in current.fields}
        manual = {override.field_id: override.value for override in item.overrides}
        original_csv_issues = self._export.csv_issues(
            context,
            {identifier: value.value for identifier, value in originals.items()},
        )
        csv_issues = self._export.csv_issues(
            context, {identifier: value.value for identifier, value in resolved.items()}
        )
        fields: list[PublicationFieldDTO] = []
        for field in context.schema.fields:
            settings = field.type_definition
            constraints = settings.constraints
            money = settings if isinstance(settings, MoneyFieldTypeVO) else None
            inherited = originals.get(field.id.uuid)
            effective = resolved.get(field.id.uuid)
            raw = manual.get(field.id)
            fields.append(
                PublicationFieldDTO(
                    field_id=field.id.uuid,
                    label=field.label.value,
                    kind=settings.kind,
                    required=constraints.required,
                    min_length=(
                        None
                        if isinstance(settings, MoneyFieldTypeVO)
                        else settings.constraints.min_length
                    ),
                    max_length=(
                        None
                        if isinstance(settings, MoneyFieldTypeVO)
                        else settings.constraints.max_length
                    ),
                    min_amount=(
                        format(money.constraints.min_amount, "f")
                        if money and money.constraints.min_amount is not None
                        else None
                    ),
                    max_amount=(
                        format(money.constraints.max_amount, "f")
                        if money and money.constraints.max_amount is not None
                        else None
                    ),
                    currency=(
                        money.currency.value
                        if money and money.currency is not None
                        else None
                    ),
                    has_override=field.id in manual,
                    override_value=(
                        format(raw.amount, "f")
                        if isinstance(raw, PriceAmountVO)
                        else raw
                    ),
                    original_value=csv_cell(inherited.value) if inherited else None,
                    resolved_value=csv_cell(effective.value) if effective else None,
                    original_issues=tuple(
                        issue.message
                        for issue in (*original.issues, *original_csv_issues)
                        if issue.field_id == field.id.uuid
                    ),
                    issues=tuple(
                        issue.message
                        for issue in (*current.issues, *csv_issues)
                        if issue.field_id == field.id.uuid
                    ),
                )
            )
        return GetPublicationFieldsResultDTO(
            context.feed.version,
            source.version,
            source.archived or context.feed.status == "ARCHIVED",
            snapshot is not None,
            tuple(fields),
        )
