from uuid import UUID

from pydantic import BaseModel

from src.modules.crm.application.contact_point.dto import ContactPointsDTO


class PutContactContactPointItemResponse(BaseModel):
    binding_id: UUID
    contact_point_id: UUID
    value: str
    country_code: str | None
    label_id: UUID | None
    position: int


class PutContactContactPointsResponse(BaseModel):
    phones: list[PutContactContactPointItemResponse]
    emails: list[PutContactContactPointItemResponse]

    @classmethod
    def from_dto(cls, dto: ContactPointsDTO) -> "PutContactContactPointsResponse":
        return cls(
            phones=[
                PutContactContactPointItemResponse(
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
                PutContactContactPointItemResponse(
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
