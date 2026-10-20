from src.modules.channels.application.product_representation.contracts import (
    CatalogDraftValuesDTO,
    PublicationCatalogSourceDTO,
)


def proposed_draft(
    source: PublicationCatalogSourceDTO, locale: str
) -> CatalogDraftValuesDTO:
    """Предлагает только известные core-значения без переводов и округлений."""
    quantified = source.quantity is not None
    return CatalogDraftValuesDTO(
        {
            locale: (
                source.title if source.title_locale == locale and source.title else ""
            )
        },
        source.external_sku,
        source.price,
        source.sale_price,
        source.currency if source.price is not None else None,
        quantified,
        source.quantity,
        (
            None
            if quantified
            else source.stock_status if source.stock_status != "unknown" else None
        ),
        "no",
    )
