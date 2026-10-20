from src.modules.shared.infrastructure.content.rich_text import sanitize_rich_text
import nh3
from src.modules.channels.application.plugin_contract import PublicationImageDTO
from src.modules.channels.application.port.plugin_services import PluginCallError
from src.modules.channels.infrastructure.plugin.core_normalizer import safe_url


def content_body(value: object) -> str | None:
    """Очищает описание до preview тем же разрешённым набором HTML, что Catalog."""
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 300000:
        raise PluginCallError("invalid_publication_description")
    return sanitize_rich_text(value)


def gallery(
    rows: list[tuple[object, object, object]],
) -> tuple[PublicationImageDTO, ...]:
    """Сохраняет порядок без дублей URL и не теряет невалидные фото молча."""
    images: list[PublicationImageDTO] = []
    seen: set[str] = set()
    for identifier, value, alt in rows:
        if (
            isinstance(identifier, bool)
            or not isinstance(identifier, (str, int))
            or not str(identifier)
            or len(str(identifier)) > 200
        ):
            raise PluginCallError("invalid_publication_gallery")
        url = safe_url(value, [])
        if not url:
            raise PluginCallError("invalid_publication_image_url")
        if url in seen:
            continue
        seen.add(url)
        images.append(
            PublicationImageDTO(
                str(identifier)[:200],
                url,
                nh3.clean(alt, tags=set())[:1000] if isinstance(alt, str) else "",
            )
        )
    if len(images) > 100:
        raise PluginCallError("publication_gallery_limit_exceeded")
    if len({i.id for i in images}) != len(images):
        raise PluginCallError("invalid_publication_gallery")
    return tuple(images)
