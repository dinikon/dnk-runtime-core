class StaticDealCurrencyCatalog:
    """Заменяемая валютная политика первого среза CRM."""

    def list(self) -> tuple[tuple[str, str], ...]:
        """Не сокращает глобальные справочники соседних модулей."""
        return (("USD", "Доллар США"), ("EUR", "Евро"), ("UAH", "Украинская гривна"))
