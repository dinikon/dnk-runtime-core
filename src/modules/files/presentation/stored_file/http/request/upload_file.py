from uuid import UUID
from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict


class UploadFileRequest(BaseModel):
    """Multipart-контракт одного файла и необязательного диска без tenant/actor."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    file: UploadFile
    bucket_id: UUID | None = None
