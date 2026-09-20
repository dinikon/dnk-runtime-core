from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from src.modules.price_lists.domain.price_list.error import PriceListValidationError


def mask_source_url(value: str) -> str:
    parsed = urlsplit(value)
    segments = [segment for segment in parsed.path.split("/") if segment]
    path = "/…/" + segments[-1] if segments else "/"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


@dataclass(slots=True, frozen=True)
class SourceUrlVO:
    """HTTPS URL без userinfo и нестандартного порта."""

    value: str

    def __post_init__(self):
        try:
            parts = urlsplit(self.value)
            if (
                parts.scheme != "https"
                or not parts.hostname
                or parts.username
                or parts.password
                or parts.port not in (None, 443)
            ):
                raise PriceListValidationError(
                    "Source must use HTTPS without credentials or a custom port."
                )
        except ValueError:
            raise PriceListValidationError("Invalid source URL.") from None


__all__ = ["SourceUrlVO", "mask_source_url"]
