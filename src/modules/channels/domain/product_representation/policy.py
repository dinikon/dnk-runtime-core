from src.modules.channels.domain.error import ChannelsConflictError


def ensure_linking_allowed(archived: bool) -> None:
    """Запрещает новые связи архивированного источника независимо от sync/pause."""
    if archived:
        raise ChannelsConflictError("channel_archived")


def ensure_target_available(status: str) -> None:
    """Ограничивает новые основные связи самостоятельными активными/Draft товарами."""
    if status not in ("draft", "active"):
        raise ChannelsConflictError("catalog_item_archived")
