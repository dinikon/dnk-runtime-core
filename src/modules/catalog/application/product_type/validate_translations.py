from src.modules.catalog.application.product_type.port.locale_reader import (
    ProductTypeLocaleReaderPort,
)
from src.modules.catalog.domain.product_type.error import InvalidProductTypeError


async def validate_active_translations(
    translations: dict[str, str], locales: ProductTypeLocaleReaderPort
) -> None:
    for code in translations:
        if not await locales.is_active(code):
            raise InvalidProductTypeError("Locale is not active.")
