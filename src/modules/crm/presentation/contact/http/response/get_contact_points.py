from uuid import UUID

from pydantic import BaseModel

from src.modules.crm.application.contact_point.dto import ContactPointsDTO


class GetContactContactPointItemResponse(BaseModel):
    binding_id: UUID
    contact_point_id: UUID
    value: str
    country_code: str | None
    label_id: UUID | None
    position: int


class GetContactContactPointsResponse(BaseModel):
    phones: list[GetContactContactPointItemResponse]
    emails: list[GetContactContactPointItemResponse]

    @classmethod
    def from_dto(cls, dto: ContactPointsDTO) -> "GetContactContactPointsResponse":
        return cls(
            phones=[
                GetContactContactPointItemResponse(
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
                GetContactContactPointItemResponse(
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
