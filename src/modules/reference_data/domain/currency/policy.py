class CurrencyMetalPolicy:
    """Отличает ISO-коды банковских металлов от валют справочника."""

    @staticmethod
    def is_metal(code: str) -> bool:
        """Определяет четыре банковских металла по стабильным ISO-кодам."""
        return code in {"XAU", "XAG", "XPT", "XPD"}
