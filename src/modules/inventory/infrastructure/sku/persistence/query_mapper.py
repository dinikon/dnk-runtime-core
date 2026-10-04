from sqlalchemy.engine import RowMapping

from src.modules.inventory.application.sku.query.get_sku.dto import SkuDetailsDTO


class SkuQueryMapper:
    """Явное преобразование SQL-проекции в application DTO."""

    @staticmethod
    def to_details(row: RowMapping) -> SkuDetailsDTO:
        """Возвращает учётные данные и аудит без восстановления Domain."""
        return SkuDetailsDTO(
            id=row["id"],
            code=row["code"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            updated_by=row["updated_by"],
        )
