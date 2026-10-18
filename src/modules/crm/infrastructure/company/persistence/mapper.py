from sqlalchemy.engine import RowMapping

from src.modules.crm.domain.company.aggregate import CompanyEntity
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.domain.company.value_object.legal_name import CompanyLegalNameVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CompanyMapper:
    """Явное преобразование агрегата в существующую SQL-модель."""

    @staticmethod
    def to_insert_values(company: CompanyEntity) -> dict[str, object]:
        return {
            "id": company.id.uuid,
            "legal_name": company.legal_name.value,
            "created_at": company.created_at,
            "updated_at": company.updated_at,
            "created_by": company.created_by.uuid,
            "updated_by": company.updated_by.uuid,
        }

    @staticmethod
    def to_entity(row: RowMapping) -> CompanyEntity:
        return CompanyEntity(
            id=CompanyIdVO.from_value(row["id"]),
            legal_name=CompanyLegalNameVO(row["legal_name"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO.from_value(row["created_by"]),
            updated_by=EntityIdVO.from_value(row["updated_by"]),
        )

    @staticmethod
    def to_update_values(company: CompanyEntity) -> dict[str, object]:
        return {
            "legal_name": company.legal_name.value,
            "updated_at": company.updated_at,
            "updated_by": company.updated_by.uuid,
        }
