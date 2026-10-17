from pydantic import BaseModel, ConfigDict


class PutCompanyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    legal_name: str
