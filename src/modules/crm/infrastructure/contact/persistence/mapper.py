from src.modules.crm.domain.contact.aggregate import Contact


class ContactMapper:
    """Явно преобразует агрегат контакта в представление хранения."""

    @staticmethod
    def to_insert_values(contact: Contact) -> dict[str, object]:
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
