from src.modules.inventory.domain.sku.aggregate import Sku


class SkuMapper:
    """Преобразование самостоятельного агрегата в значения tenant-таблицы."""

    @staticmethod
    def to_insert_values(sku: Sku) -> dict[str, object]:
        """Сохраняет значения VO и явный аудит."""
        return dict(
            id=sku.id.uuid,
            code=sku.code.value,
            title=sku.title.value,
            created_at=sku.created_at,
            updated_at=sku.updated_at,
            created_by=sku.created_by.uuid,
            updated_by=sku.updated_by.uuid,
        )
