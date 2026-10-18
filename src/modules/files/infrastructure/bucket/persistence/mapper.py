from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from typing import Any
from src.modules.files.domain.bucket.aggregate import Bucket
from src.modules.files.infrastructure.persistence.models.bucket import BucketModel
from src.modules.files.domain.value_object.bucket_name import BucketNameVO


class BucketMapper:
    """Преобразует представление хранения без I/O и предметных правил."""

    @staticmethod
    def to_domain(row: BucketModel) -> Bucket:
        """Восстанавливает агрегат через его явную фабрику."""
        return Bucket.restore(
            bucket_id=EntityIdVO.from_value(row.id),
            provider_id=EntityIdVO.from_value(row.provider_id),
            name=BucketNameVO(row.name),
            status=row.status,
        )

    @staticmethod
    def to_insert_values(aggregate: Bucket) -> dict[str, Any]:
        """Извлекает значения для записи без самостоятельного INSERT."""
        return {
            "id": aggregate.id.uuid,
            "provider_id": aggregate.provider_id.uuid,
            "name": aggregate.name.value,
            "status": aggregate.status,
        }

    @staticmethod
    def to_update_values(aggregate: Bucket) -> dict[str, Any]:
        """Извлекает сохраняемое состояние агрегата."""
        return BucketMapper.to_insert_values(aggregate)
