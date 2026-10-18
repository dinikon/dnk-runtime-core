from uuid import UUID

from pydantic import BaseModel

from src.modules.crm.application.contact_point.dto import ContactPointsDTO


class PatchCompanyContactPointItemResponse(BaseModel):
    binding_id: UUID
    contact_point_id: UUID
    value: str
    country_code: str | None
    label_id: UUID | None
    position: int


class PatchCompanyContactPointsResponse(BaseModel):
    phones: list[PatchCompanyContactPointItemResponse]
    emails: list[PatchCompanyContactPointItemResponse]

    @classmethod
    def from_dto(cls, dto: ContactPointsDTO) -> "PatchCompanyContactPointsResponse":
        return cls(
            phones=[
                PatchCompanyContactPointItemResponse(
                    binding_id=item.binding_id,
                    contact_point_id=item.contact_point_id,
                    value=item.value,
                    country_code=item.country_code,
                    label_id=item.label_id,
                    position=item.position,
                )
                for item in dto.phones
            ],
            emails=[
                PatchCompanyContactPointItemResponse(
                    binding_id=item.binding_id,
                    contact_point_id=item.contact_point_id,
                    value=item.value,
                    country_code=item.country_code,
                    label_id=item.label_id,
                    position=item.position,
                )
                for item in dto.emails
            ],
        )
