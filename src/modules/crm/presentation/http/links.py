from uuid import UUID
from pydantic import BaseModel
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.crm.domain.contact.value_object import ContactIdVO


class CrmLinkResponse(BaseModel):
    id: UUID
    name: str


def link_inputs(payload, field, identifier_type):
    result = {field: None}
    if field in payload.model_fields_set:
        result[field] = tuple(
            identifier_type.from_value(value) for value in getattr(payload, field)
        )
    expected = "expected_" + field
    if hasattr(payload, expected):
        result[expected] = (
            tuple(
                identifier_type.from_value(value)
                for value in getattr(payload, expected)
            )
            if expected in payload.model_fields_set
            else None
        )
    return result
