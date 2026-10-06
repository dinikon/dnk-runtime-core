from enum import StrEnum


class ChannelType(StrEnum):
    """Категория платформы для группировки каталога."""

    CMS = "cms"
    MARKETPLACE = "marketplace"
    SHOP = "shop"
