from dataclasses import dataclass
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode


@dataclass(frozen=True, slots=True)
class GetProviderStatusQuery:
    """Input for get provider status."""

    provider: ProviderCode


__all__ = ["GetProviderStatusQuery"]
