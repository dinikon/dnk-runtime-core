from src.modules.catalog.application.content_block.port.locale_reader import (
    ContentBlockLocaleReaderPort,
)
from src.modules.catalog.domain.content_block.error import InvalidContentBlockError


async def validate_active_translations(
    translations: dict[str, str], locales: ContentBlockLocaleReaderPort
) -> None:
    for code in translations:
        if not await locales.is_active(code):
            raise InvalidContentBlockError("Locale is not active.")
