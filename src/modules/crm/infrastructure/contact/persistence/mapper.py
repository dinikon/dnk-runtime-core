from sqlalchemy.engine import RowMapping

from src.modules.crm.domain.contact.aggregate import ContactEntity
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.domain.contact.value_object.name import ContactNameVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContactMapper:
    """Явно преобразует агрегат контакта в представление хранения."""

    @staticmethod
    def to_insert_values(contact: ContactEntity) -> dict[str, object]:
        """Возвращает поля INSERT без SQL-запросов и создания ORM-объекта."""
        return {
            "id": contact.id.uuid,
            "first_name": contact.name.first_name,
            "last_name": contact.name.last_name,
            "middle_name": contact.name.middle_name,
            "created_at": contact.created_at,
            "updated_at": contact.updated_at,
            "created_by": contact.created_by.uuid,
            "updated_by": contact.updated_by.uuid,
        }

    @staticmethod
    def to_entity(row: RowMapping) -> ContactEntity:
        """Восстанавливает агрегат, проверяя его инвариант имени."""
        return ContactEntity(
            id=ContactIdVO.from_value(row["id"]),
            name=ContactNameVO(
                first_name=row["first_name"],
                last_name=row["last_name"],
                middle_name=row["middle_name"],
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO.from_value(row["created_by"]),
            updated_by=EntityIdVO.from_value(row["updated_by"]),
        )

    @staticmethod
    def to_update_values(contact: ContactEntity) -> dict[str, object]:
        """Переносит изменяемые поля агрегата в UPDATE."""
        return {
            "first_name": contact.name.first_name,
            "last_name": contact.name.last_name,
            "middle_name": contact.name.middle_name,
            "updated_at": contact.updated_at,
            "updated_by": contact.updated_by.uuid,
        }
