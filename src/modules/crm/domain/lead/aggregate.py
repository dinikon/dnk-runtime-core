from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.sales_error import SalesError, SalesConflictError
from src.modules.crm.domain.value_object.funnel_position import FunnelPositionVO
from src.modules.crm.domain.value_object.sale_text import sale_text


@dataclass(slots=True)
class Lead:
    """Самостоятельный лид с независимым снимком обращения."""

    id: EntityIdVO
    title: str
    position: FunnelPositionVO
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    company_name: str | None
    contact_id: EntityIdVO | None
    company_id: EntityIdVO | None
    conversion_result: dict[str, object] | None
    conversion_key: str | None
    conversion_fingerprint: str | None

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
            first_name=None,
            last_name=None,
            middle_name=None,
            company_name=None,
            contact_id=None,
            company_id=None,
            conversion_result=None,
            conversion_key=None,
            conversion_fingerprint=None,
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
        if result.conversion_result is None and (
            result.conversion_key or result.conversion_fingerprint
        ):
            raise SalesError("Повреждён результат конвертации.")
        return result

    def ensure_editable(self) -> None:
        """Проверяет допустимость изменения независимо от названия стадии."""
        if self.conversion_result is not None:
            raise SalesConflictError(
                "Лид уже конвертирован и доступен только для чтения."
            )

    def revise(
        self, *, fields: dict[str, object], actor_id: EntityIdVO, now: datetime
    ) -> None:
        """Проверяет весь кандидат до изменения собственных полей."""
        self.ensure_editable()
        candidate = {}
        for key, value in fields.items():
            if key == "title":
                candidate[key] = sale_text(value, key, required=True)
            elif key in (
                "first_name",
                "last_name",
                "middle_name",
                "company_name",
                "contact_id",
                "company_id",
            ):
                candidate[key] = (
                    sale_text(value, key)
                    if key.endswith("name")
                    else (EntityIdVO.from_value(value) if value is not None else None)
                )
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

    def complete_conversion(
        self,
        *,
        result: dict[str, object],
        key: str,
        fingerprint: str,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> None:
        """Однократно сохраняет результаты и блокирует исходный лид."""
        self.ensure_editable()
        self.conversion_result = dict(result)
        self.conversion_key = key
        self.conversion_fingerprint = fingerprint
        self.updated_at = now
        self.updated_by = EntityIdVO.from_value(actor_id)

    def touch(self, *, actor_id: EntityIdVO, now: datetime) -> None:
        """Отмечает разрешённое изменение связанных коммерческих данных."""
        self.ensure_editable()
        self.updated_at = now
        self.updated_by = EntityIdVO.from_value(actor_id)

    def relocate_after_stage_deletion(
        self,
        *,
        funnel_id: EntityIdVO,
        stage_id: EntityIdVO,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> None:
        """Системно меняет только позицию и аудит, сохраняя жизненный цикл."""
        if self.position.funnel_id != EntityIdVO.from_value(funnel_id):
            raise SalesConflictError("Карточка уже находится в другой воронке.")
        position = self.position.move(funnel_id, stage_id, self.position.revision)
        if position != self.position:
            self.position = position
            self.updated_at = now
            self.updated_by = EntityIdVO.from_value(actor_id)
