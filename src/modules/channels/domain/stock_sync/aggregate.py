from dataclasses import dataclass
from datetime import datetime

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.stock_sync.error import StockSyncError
from src.modules.channels.domain.stock_sync.value_object import (
    StockDirection,
    StockSyncStatus,
    StockSnapshotVO,
)


@dataclass(slots=True)
class StockSync:
    """Одно состояние и одно поколение задания на физический остаток площадки."""

    publication_id: EntityIdVO
    connection_id: EntityIdVO
    operation_id: EntityIdVO
    direction: StockDirection
    status: StockSyncStatus
    revision: int
    config_revision: int
    policy_revision: int
    binding_group_id: EntityIdVO
    binding_revision: int
    observed: StockSnapshotVO | None
    observed_at: datetime | None
    desired_quantity: int | None
    error_code: str | None
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        publication_id: EntityIdVO,
        connection_id: EntityIdVO,
        operation_id: EntityIdVO,
        direction: StockDirection,
        config_revision: int,
        policy_revision: int,
        binding_group_id: EntityIdVO,
        binding_revision: int,
        now: datetime,
    ) -> "StockSync":
        """Начинает первый запрос без придуманного наблюдаемого количества."""
        return cls.restore(
            publication_id=publication_id,
            connection_id=connection_id,
            operation_id=operation_id,
            direction=direction,
            status="queued",
            revision=1,
            config_revision=config_revision,
            policy_revision=policy_revision,
            binding_group_id=binding_group_id,
            binding_revision=binding_revision,
            observed=None,
            observed_at=None,
            desired_quantity=None,
            error_code=None,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        publication_id: EntityIdVO,
        connection_id: EntityIdVO,
        operation_id: EntityIdVO,
        direction: StockDirection,
        status: StockSyncStatus,
        revision: int,
        config_revision: int,
        policy_revision: int,
        binding_group_id: EntityIdVO,
        binding_revision: int,
        observed: StockSnapshotVO | None,
        observed_at: datetime | None,
        desired_quantity: int | None,
        error_code: str | None,
        updated_at: datetime,
    ) -> "StockSync":
        """Отклоняет противоречивое состояние до создания агрегата."""
        if (
            not all(
                isinstance(v, EntityIdVO)
                for v in (publication_id, connection_id, operation_id, binding_group_id)
            )
            or any(
                type(v) is not int or v < 1
                for v in (revision, config_revision, policy_revision, binding_revision)
            )
            or not isinstance(direction, str)
            or direction not in {"read", "write"}
            or not isinstance(status, str)
            or status not in {"queued", "running", "completed", "failed", "cancelled"}
            or (observed is None) != (observed_at is None)
            or (observed is not None and not isinstance(observed, StockSnapshotVO))
            or (
                desired_quantity is not None
                and (
                    type(desired_quantity) is not int
                    or not 0 <= desired_quantity <= 2147483647
                )
            )
            or (direction == "read" and desired_quantity is not None)
            or (
                error_code is not None
                and (not isinstance(error_code, str) or not error_code.strip())
            )
            or (status == "queued" and desired_quantity is not None)
            or (
                status in {"running", "completed"}
                and direction == "write"
                and desired_quantity is None
            )
            or (status == "failed") != (error_code is not None)
            or (status == "completed" and observed is None)
            or not isinstance(updated_at, datetime)
            or updated_at.tzinfo is None
            or (
                observed_at is not None
                and (
                    not isinstance(observed_at, datetime)
                    or observed_at.tzinfo is None
                    or observed_at > updated_at
                )
            )
        ):
            raise StockSyncError("stock_state_invalid")
        return cls(
            publication_id,
            connection_id,
            operation_id,
            direction,
            status,
            revision,
            config_revision,
            policy_revision,
            binding_group_id,
            binding_revision,
            observed,
            observed_at,
            desired_quantity,
            error_code,
            updated_at,
        )

    def accepts_access(
        self,
        *,
        connection_id: EntityIdVO,
        config_revision: int,
        policy_revision: int,
        verified: bool,
        export_allowed: bool,
    ) -> bool:
        """Старый доступ или отключённая отправка не принимают результат операции."""
        return (
            self.connection_id == connection_id
            and self.config_revision == config_revision
            and verified
            and (
                self.direction == "read"
                or (export_allowed and self.policy_revision == policy_revision)
            )
        )

    def request(
        self,
        *,
        operation_id: EntityIdVO,
        direction: StockDirection,
        config_revision: int,
        policy_revision: int,
        binding_group_id: EntityIdVO,
        binding_revision: int,
        now: datetime,
    ) -> None:
        """Заменяет ожидающее поколение, сохраняя последнее наблюдение."""
        self._require_time(now)
        candidate = self.restore(
            publication_id=self.publication_id,
            connection_id=self.connection_id,
            operation_id=operation_id,
            direction=direction,
            status="queued",
            revision=self.revision + 1,
            config_revision=config_revision,
            policy_revision=policy_revision,
            binding_group_id=binding_group_id,
            binding_revision=binding_revision,
            observed=self.observed,
            observed_at=self.observed_at,
            desired_quantity=None,
            error_code=None,
            updated_at=now,
        )
        self._replace(candidate)

    def start(
        self, *, operation_id: EntityIdVO, quantity: int | None, now: datetime
    ) -> bool:
        """Старое или повторно завершённое задание не получает право записи."""
        self._require_time(now)
        if operation_id != self.operation_id or self.status not in {
            "queued",
            "running",
        }:
            return False
        if (
            self.direction == "write"
            and (type(quantity) is not int or not 0 <= quantity <= 2147483647)
        ) or (self.direction == "read" and quantity is not None):
            raise StockSyncError("stock_quantity_invalid")
        self.status, self.desired_quantity, self.updated_at = "running", quantity, now
        self.revision += 1
        return True

    def complete(
        self,
        *,
        operation_id: EntityIdVO,
        snapshot: StockSnapshotVO | None,
        error_code: str | None,
        now: datetime,
    ) -> bool:
        """Применяет только актуальный результат и сохраняет прошлое наблюдение при ошибке."""
        self._require_time(now)
        if operation_id != self.operation_id or self.status != "running":
            return False
        if (snapshot is None) == (error_code is None):
            raise StockSyncError("stock_result_invalid")
        if error_code is not None and (
            not isinstance(error_code, str) or not error_code.strip()
        ):
            raise StockSyncError("stock_result_invalid")
        if snapshot is not None:
            if not isinstance(snapshot, StockSnapshotVO):
                raise StockSyncError("stock_snapshot_invalid")
            self.observed, self.observed_at = snapshot, now
        self.status = "failed" if error_code else "completed"
        self.error_code, self.updated_at = error_code, now
        self.revision += 1
        return True

    def cancel(self, *, now: datetime) -> None:
        """Инвалидирует задание без потери последнего полученного количества."""
        self._require_time(now)
        if self.status in {"queued", "running"}:
            self.status, self.error_code, self.updated_at = "cancelled", None, now
            self.revision += 1

    def reject(
        self, *, operation_id: EntityIdVO, error_code: str, now: datetime
    ) -> None:
        """Сохраняет отказ подготовки без выдуманного желаемого количества."""
        self._require_time(now)
        if operation_id != self.operation_id or self.status not in {
            "queued",
            "running",
        }:
            return
        if not isinstance(error_code, str) or not error_code.strip():
            raise StockSyncError("stock_result_invalid")
        self.status, self.error_code, self.updated_at = "failed", error_code, now
        self.revision += 1

    def _require_time(self, now: datetime) -> None:
        """Отклоняет некорректное время до любых изменений."""
        if not isinstance(now, datetime) or now.tzinfo is None or now < self.updated_at:
            raise StockSyncError("stock_state_invalid")

    def _replace(self, candidate: "StockSync") -> None:
        """Переносит проверенного кандидата без частичного изменения."""
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(candidate, name))
