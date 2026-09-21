from src.modules.currency.presentation.http.request import RequestModel


class EnabledRequest(RequestModel):
    """Validated HTTP input for enabled request."""

    enabled: bool


__all__ = ["EnabledRequest"]
