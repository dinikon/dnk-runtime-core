class InvalidInventoryItemUpdateError(Exception):
    """Отклоняет пустую команду, неизвестные поля и явно переданные null."""
