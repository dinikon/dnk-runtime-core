from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthorizeContentDeliveryResultDTO:
    """Результат конкретного сценария authorize_content_delivery."""

    allowed: bool
