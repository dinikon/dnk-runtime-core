from pydantic import BaseModel


class ProviderCapabilitiesResponse(BaseModel):
    """Validated HTTP output for provider capabilities response."""

    historical_rates: bool
    supported_currencies: bool
    base_currency: str | None
    bulk_download: bool


class RateSourceResponse(BaseModel):
    """Validated HTTP output for rate source response."""

    code: str
    local: bool
    capabilities: ProviderCapabilitiesResponse


__all__ = ["RateSourceResponse", "ProviderCapabilitiesResponse"]
