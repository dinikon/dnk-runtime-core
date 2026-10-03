from sqlalchemy.engine import RowMapping

from src.modules.crm.application.company.query.get_company.dto import CompanyDetailsDTO


class CompanyQueryMapper:
    @staticmethod
    def to_details(row: RowMapping) -> CompanyDetailsDTO:
        return CompanyDetailsDTO(
            id=row["id"],
            legal_name=row["legal_name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            updated_by=row["updated_by"],
        )
