from enum import StrEnum


class TenantServiceType(StrEnum):
    CONSOLE = "console"
    API = "http"
    SHORTLINKS = "shortlinks"
