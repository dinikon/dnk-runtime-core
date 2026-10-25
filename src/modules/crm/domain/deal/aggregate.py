from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.sales_error import SalesError, SalesConflictError
from src.modules.crm.domain.value_object.funnel_position import FunnelPositionVO
from src.modules.crm.domain.value_object.sale_text import sale_text


@dataclass(slots=True)
class Deal:
    """Самостоятельный единый объект продажи без Order."""

    id: EntityIdVO
    title: str
    position: FunnelPositionVO
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    contact_ids: tuple[EntityIdVO, ...]
    company_ids: tuple[EntityIdVO, ...]
    source_lead_id: EntityIdVO | None
    source_lead_snapshot: dict[str, str | None] | None
    lifecycle_state: str

    @classmethod
    def create(
        cls,
        *,
        record_id: EntityIdVO,
        title: str,
        position: FunnelPositionVO,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт карточку с первоначальной позицией и аудитом."""
        return cls(
            id=EntityIdVO.from_value(record_id),
            title=sale_text(title, "title", required=True),
            position=position,
            created_at=now,
            updated_at=now,
            created_by=EntityIdVO.from_value(actor_id),
            updated_by=EntityIdVO.from_value(actor_id),
            contact_ids=(),
            company_ids=(),
            source_lead_id=None,
            source_lead_snapshot=None,
            lifecycle_state="draft",
        )

    @classmethod
    def restore(cls, **values: object) -> Self:
        """Восстанавливает проверенную сохранённую карточку."""
        values = dict(values)
        for key in (
            "id",
            "created_by",
            "updated_by",
            "contact_id",
            "company_id",
            "source_lead_id",
        ):
            if key in values and values[key] is not None:
                values[key] = EntityIdVO.from_value(values[key])
        for key in ("contact_ids", "company_ids"):
            if key in values:
                values[key] = tuple(EntityIdVO.from_value(v) for v in values[key])
        values["title"] = sale_text(values["title"], "title", required=True)
        result = cls(**values)
        if result.lifecycle_state != "draft":
            raise SalesError("Неизвестное состояние продажи.")
        result._validate_participants(result.contact_ids)
        result._validate_participants(result.company_ids)
        return result

    def ensure_editable(self) -> None:
        """Проверяет допустимость изменения независимо от названия стадии."""
        if self.lifecycle_state != "draft":
            raise SalesConflictError("Продажа не допускает редактирования.")

    def revise(
        self, *, fields: dict[str, object], actor_id: EntityIdVO, now: datetime
    ) -> None:
        """Проверяет весь кандидат до изменения собственных полей."""
        self.ensure_editable()
        candidate = {}
        for key, value in fields.items():
            if key == "title":
                candidate[key] = sale_text(value, key, required=True)
            elif key in ("contact_ids", "company_ids"):
                candidate[key] = tuple(EntityIdVO.from_value(v) for v in value)
                self._validate_participants(candidate[key])
            else:
                raise SalesError(f"Поле {key} нельзя менять.")
        if any(getattr(self, k) != v for k, v in candidate.items()):
            for key, value in candidate.items():
                setattr(self, key, value)
            self.updated_at = now
            self.updated_by = EntityIdVO.from_value(actor_id)

    def move(
        self,
        *,
        funnel_id: EntityIdVO,
        stage_id: EntityIdVO,
        expected_revision: int,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> None:
        """Перемещает карточку с проверкой версии позиции."""
        self.ensure_editable()
        position = self.position.move(funnel_id, stage_id, expected_revision)
        if position != self.position:
            self.position = position
            self.updated_at = now
            self.updated_by = EntityIdVO.from_value(actor_id)

    @staticmethod
    def _validate_participants(ids: tuple[EntityIdVO, ...]) -> None:
        """Проверяет идентичности участников, не объединяя одноимённые записи."""
        if (
            len(ids) > 100
            or any(not isinstance(i, EntityIdVO) for i in ids)
            or len(set(ids)) != len(ids)
        ):
            raise SalesError(
                "Участники должны иметь уникальные EntityIdVO, не более 100."
            )

    def set_lead_origin(
        self, lead_id: EntityIdVO, snapshot: dict[str, str | None]
    ) -> None:
        """Однократно назначает неизменяемое происхождение новой продажи."""
        if self.source_lead_id is not None:
            raise SalesConflictError("Источник продажи уже назначен.")
        self.source_lead_id = EntityIdVO.from_value(lead_id)
        self.source_lead_snapshot = dict(snapshot)

    def touch(self, *, actor_id: EntityIdVO, now: datetime) -> None:
        """Отмечает разрешённое изменение связанных коммерческих данных."""
        self.ensure_editable()
        self.updated_at = now
        self.updated_by = EntityIdVO.from_value(actor_id)
