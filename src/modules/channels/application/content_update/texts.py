from src.modules.channels.application.plugin_contract import PublicationTranslationDTO
from src.modules.channels.domain.content_update.value_object.texts import (
    ContentTextsVO,
    LocalizedTextVO,
)
from src.modules.channels.domain.error import ChannelsValidationError


def content_texts(
    translations: tuple[PublicationTranslationDTO, ...], locales: tuple[str, ...]
) -> ContentTextsVO:
    """Не допускает fallback, лишние или отсутствующие локали в результате плагина."""
    if len(translations) != len(locales) or {
        text.locale for text in translations
    } != set(locales):
        raise ChannelsValidationError("content_update_locales_mismatch")
    by_locale = {text.locale: text for text in translations}
    return ContentTextsVO(
        tuple(
            LocalizedTextVO(locale, by_locale[locale].title, by_locale[locale].body)
            for locale in locales
        )
    )


def plugin_texts(texts: ContentTextsVO) -> tuple[PublicationTranslationDTO, ...]:
    """Преобразует собственный снимок в immutable SDK контракт."""
    return tuple(
        PublicationTranslationDTO(text.locale, text.title, text.body)
        for text in texts.translations
    )
