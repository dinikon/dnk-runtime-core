from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.domain.value_object.bucket_name import BucketNameVO
from src.modules.files.domain.error import InvalidStorageStateError


@dataclass(slots=True)
class Bucket:
    """Приватный контейнер с возобновляемой подготовкой."""

    id: EntityIdVO
    provider_id: EntityIdVO
    name: BucketNameVO
    status: str

    @classmethod
    def create(
        cls, *, bucket_id: EntityIdVO, provider_id: EntityIdVO, name: BucketNameVO
    ) -> "Bucket":
        """Создаёт приватный контейнер в состоянии подготовки."""
        return cls(bucket_id, provider_id, name, "preparing")

    @classmethod
    def restore(
        cls,
        *,
        bucket_id: EntityIdVO,
        provider_id: EntityIdVO,
        name: BucketNameVO,
        status: str,
    ) -> "Bucket":
        """Восстанавливает зарегистрированный контейнер."""
        if status not in {"preparing", "ready", "purged"}:
            raise InvalidStorageStateError("Invalid bucket status.")
        return cls(bucket_id, provider_id, name, status)

    def mark_ready(self) -> None:
        """Подтверждает подготовку, запрещая восстановление удалённого контейнера."""
        if self.status == "purged":
            raise InvalidStorageStateError("Bucket was purged.")
        self.status = "ready"

    def ensure_ready(self) -> None:
        """Допускает файловые операции только после успешной подготовки."""
        if self.status != "ready":
            raise InvalidStorageStateError("Bucket is not ready.")

    def mark_purged(self) -> None:
        """Фиксирует подтверждённое физическое удаление контейнера."""
        self.status = "purged"
