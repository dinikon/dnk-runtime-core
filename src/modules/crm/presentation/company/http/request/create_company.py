from pydantic import BaseModel, ConfigDict


class CreateCompanyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    legal_name: str
