from src.modules.feed_builder.application.publication.port.query_repository import (
    PublicationRecord,
)
from src.modules.feed_builder.application.publication.port.catalog_subjects import (
    PublicationCatalogReaderProtocol,
)
from src.modules.feed_builder.application.publication.query.list_publications.dto import (
    PublicationListItemDTO,
)
from src.modules.feed_builder.domain.publication.value_object.catalog_product_reference import (
    CatalogProductReferenceVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def enrich_publications(
    records: tuple[PublicationRecord, ...],
    catalog: PublicationCatalogReaderProtocol,
    locale: str,
) -> tuple[PublicationListItemDTO, ...]:
    """Пакетно обогащает только текущую страницу и явно сохраняет отсутствующие источники."""
    references = tuple(
        CatalogProductReferenceVO(
            EntityIdVO(r.catalog_item_id),
            EntityIdVO(r.catalog_variant_id) if r.catalog_variant_id else None,
        )
        for r in records
    )
    subjects = {s.reference: s for s in await catalog.read_many(references, locale)}
    result: list[PublicationListItemDTO] = []
    for record, ref in zip(records, references):
        source = subjects.get(ref)
        result.append(
            PublicationListItemDTO(
                record,
                source.kind if source else None,
                source.title if source else None,
                source.parent_title if source else None,
                source.sku if source else None,
                source.available if source else False,
            )
        )
    return tuple(result)
