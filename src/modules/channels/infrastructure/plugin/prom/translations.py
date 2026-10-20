from typing import Literal
from src.modules.channels.application.plugin_contract import ProviderJsonValue
from src.modules.channels.application.port.plugin_services import PluginCallError


def localized_field(
    row: dict[str, ProviderJsonValue],
    field: Literal["name", "description"],
    locale: str,
) -> ProviderJsonValue:
    """Читает язык из multilang; scalar допускается только для основного ru."""
    translations = row.get(field + "_multilang")
    if translations is None:
        return row.get(field) if locale == "ru" else None
    if not isinstance(translations, dict):
        raise PluginCallError("invalid_publication_translation")
    return translations.get(locale)
