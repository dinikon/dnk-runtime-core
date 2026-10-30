from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplyContentDeliveryResultDTO:
    """Результат конкретного сценария apply_content_delivery."""

    applied: bool
