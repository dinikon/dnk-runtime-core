from src.modules.schema_registry.domain.error import SchemaRegistryError


class ObjectFeatureConfigLockedError(SchemaRegistryError):
    """Ошибка изменения locked object feature config."""

    pass


class ObjectFeatureConfigForbiddenError(SchemaRegistryError):
    """Ошибка запрещенной пользовательской операции над object feature config."""

    pass


class ObjectFeatureNotEnabledError(SchemaRegistryError):
    """Ошибка использования выключенной object feature."""

    pass


class ObjectFeatureConfigNotFoundError(SchemaRegistryError):
    """Ошибка поиска отсутствующего object feature config."""

    pass
