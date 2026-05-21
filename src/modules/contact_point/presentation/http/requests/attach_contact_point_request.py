from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.modules.contact_point.domain.contact_point import ContactPointTypeVO


class AttachContactPointRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_object_id: UUID
    owner_record_id: UUID
    contact_point_type: ContactPointTypeVO
    raw_value: str
    is_primary: bool = False


__all__ = ["AttachContactPointRequestSchema"]
