from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RefreshExchangeRatesCommand:
    """Запрашивает обновление книги NBU в заранее привязанном tenant-контексте."""
