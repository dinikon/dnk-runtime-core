from sqlalchemy.engine import RowMapping

from src.modules.crm.application.contact.query.get_contact.dto import ContactDetailsDTO


class ContactQueryMapper:
    """Преобразует SQL-проекцию в DTO без нормализации сохранённых данных."""

    @staticmethod
    def to_details(row: RowMapping) -> ContactDetailsDTO:
        """Явно переносит все поля карточки, сохраняя nullable-фамилию."""
        return ContactDetailsDTO(
            id=row["id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            middle_name=row["middle_name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            updated_by=row["updated_by"],
        )
