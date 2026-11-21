from src.modules.inventory.application.packaging_type.query.get_packaging_type.dto import (
    GetPackagingTypeResultDTO,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.dto import (
    PackagingTypeListItemDTO,
)
from src.modules.inventory.infrastructure.persistence.models.packaging_type import (
    PackagingTypeModel,
)


class PackagingTypeQueryMapper:
    """Преобразует типизированную ORM-модель в проекции без восстановления Domain."""

    @staticmethod
    def to_details(model: PackagingTypeModel) -> GetPackagingTypeResultDTO:
        """Собирает DTO отдельной карточки."""
        return GetPackagingTypeResultDTO(
            id=model.id, code=model.code, name=model.name, is_active=model.is_active
        )

    @staticmethod
    def to_list_item(model: PackagingTypeModel) -> PackagingTypeListItemDTO:
        """Собирает DTO строки списка."""
        return PackagingTypeListItemDTO(
            id=model.id, code=model.code, name=model.name, is_active=model.is_active
        )
